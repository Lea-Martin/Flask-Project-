import re

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Train What?</title>
<style>
  :root {
    --bg: #0e0f0c; --panel: #171914; --line: #2a2d25;
    --ink: #f1f2ea; --mute: #9a9f8c; --lime: #c8ff3d; --lime-ink: #11140a;
  }
  * { box-sizing: border-box; margin: 0; }
  body {
    background: var(--bg); color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    line-height: 1.5; padding: 0 1rem 4rem;
  }
  .wrap { max-width: 900px; margin: 0 auto; }
  header { padding: 4rem 0 2rem; }
  h1 {
    font-family: Impact, "Arial Narrow Bold", "Helvetica Neue", sans-serif;
    font-weight: 900; text-transform: uppercase; letter-spacing: -0.01em;
    font-size: clamp(3rem, 12vw, 7rem); line-height: .9;
  }
  h1 em { color: var(--lime); font-style: normal; }
  .lead { margin-top: 1rem; color: var(--mute); max-width: 48ch; }

  .panel { background: var(--panel); border: 1px solid var(--line);
           border-radius: 16px; padding: 1.25rem; }
  label.title { display: block; font-size: .75rem; text-transform: uppercase;
                letter-spacing: .12em; color: var(--mute); margin-bottom: .5rem; }
  .row { display: flex; gap: .75rem; flex-wrap: wrap; }
  input[type=text] {
    flex: 1 1 260px; background: var(--bg); color: var(--ink);
    border: 1px solid var(--line); border-radius: 12px;
    padding: .9rem 1rem; font-size: 1.05rem;
  }
  input[type=text]:focus { outline: 2px solid var(--lime); border-color: transparent; }
  button.go {
    background: var(--lime); color: var(--lime-ink); border: 0; border-radius: 12px;
    padding: .9rem 1.6rem; font-size: 1rem; font-weight: 800; cursor: pointer;
    text-transform: uppercase; letter-spacing: .05em;
  }
  button.go:hover { filter: brightness(1.08); }

  .section { margin-top: 1.25rem; }
  .chips { display: flex; flex-wrap: wrap; gap: .5rem; }
  .chip input { position: absolute; opacity: 0; pointer-events: none; }
  .chip span {
    display: inline-block; padding: .4rem .9rem; border-radius: 999px;
    border: 1px solid var(--line); cursor: pointer; font-size: .9rem;
    text-transform: capitalize; user-select: none;
  }
  .chip input:checked + span { background: var(--lime); color: var(--lime-ink);
                               border-color: var(--lime); font-weight: 700; }
  .chip input:focus-visible + span { outline: 2px solid var(--lime); outline-offset: 2px; }
  .options { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; }

  #results { margin-top: 2.5rem; }
  .msg { color: var(--mute); padding: 1rem 0; }
  .group { margin-top: 2rem; }
  .group h2 {
    font-family: Impact, "Arial Narrow Bold", sans-serif; font-weight: 900;
    text-transform: uppercase; font-size: 1.8rem; color: var(--lime);
    border-bottom: 1px solid var(--line); padding-bottom: .4rem; margin-bottom: 1rem;
  }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
  .card { background: var(--panel); border: 1px solid var(--line);
          border-radius: 14px; padding: 1rem; }
  .card h3 { font-size: 1.05rem; margin-bottom: .5rem; }
  .tags { display: flex; gap: .4rem; flex-wrap: wrap; margin-bottom: .6rem; }
  .tag { font-size: .7rem; text-transform: uppercase; letter-spacing: .08em;
         border: 1px solid var(--line); color: var(--mute); border-radius: 6px; padding: .1rem .45rem; }
  .rx { font-weight: 800; color: var(--lime); margin-bottom: .35rem; }
  .tip { color: var(--mute); font-size: .9rem; }
  .note { margin-top: 3rem; color: var(--mute); font-size: .8rem; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Train<br><em>what?</em></h1>
    <p class="lead">Tell me which part of your body you want to work on. I'll suggest exercises that fit your equipment and level.</p>
  </header>

  <form id="form" class="panel" autocomplete="off">
    <label class="title" for="text">What do you want to train?</label>
    <div class="row">
      <input id="text" type="text" placeholder="e.g. chest and triceps, stronger core, legs…">
      <button class="go" type="submit">Suggest</button>
    </div>

    <div class="section">
      <label class="title">…or tap muscles</label>
      <div class="chips" id="chips">
        {% for m in muscles %}
        <label class="chip"><input type="checkbox" value="{{ m }}"><span>{{ m }}</span></label>
        {% endfor %}
      </div>
    </div>

    <div class="section options">
      <div>
        <label class="title">Equipment you have</label>
        <div class="chips" id="equipment">
          {% for e in equipment %}
          <label class="chip"><input type="checkbox" value="{{ e }}" checked {% if e == 'bodyweight' %}disabled{% endif %}><span>{{ e }}</span></label>
          {% endfor %}
        </div>
      </div>
      <div>
        <label class="title">Your level</label>
        <div class="chips" id="levels">
          {% for l in levels %}
          <label class="chip"><input type="radio" name="level" value="{{ l }}" {% if l == 'intermediate' %}checked{% endif %}><span>{{ l }}</span></label>
          {% endfor %}
        </div>
      </div>
    </div>
  </form>

  <div id="results" aria-live="polite"></div>
  <p class="note">General fitness information, not medical advice. Warm up first, start light and stop if something hurts.</p>
</div>

<script>
const form = document.getElementById('form');
const results = document.getElementById('results');

const checked = sel => [...document.querySelectorAll(sel + ' input:checked')].map(i => i.value);

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function render(data) {
  results.replaceChildren();
  if (!data.groups.length) {
    results.append(el('p', 'msg', data.message || 'Nothing found.'));
    return;
  }
  data.groups.forEach(g => {
    const group = el('section', 'group');
    group.append(el('h2', null, g.muscle));
    const cards = el('div', 'cards');
    if (!g.exercises.length) {
      cards.append(el('p', 'msg', 'No exercises for this with your current equipment and level. Try adding equipment or raising your level.'));
    }
    g.exercises.forEach(x => {
      const c = el('article', 'card');
      c.append(el('h3', null, x.name));
      const tags = el('div', 'tags');
      [x.equipment, x.level].forEach(t => tags.append(el('span', 'tag', t)));
      c.append(tags, el('p', 'rx', x.rx), el('p', 'tip', x.tip));
      cards.append(c);
    });
    group.append(cards);
    results.append(group);
  });
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  results.replaceChildren(el('p', 'msg', 'Finding exercises…'));
  try {
    const res = await fetch('/api/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: document.getElementById('text').value,
        chips: checked('#chips'),
        equipment: checked('#equipment'),
        level: (checked('#levels')[0]) || 'intermediate',
      }),
    });
    render(await res.json());
  } catch (err) {
    results.replaceChildren(el('p', 'msg', 'Something went wrong. Is the server running?'));
  }
});
</script>
</body>
</html>
"""

MUSCLES = [
    "chest", "back", "shoulders", "biceps", "triceps", "forearms",
    "abs", "obliques", "lower back", "quads", "hamstrings", "glutes", "calves",
]
EQUIPMENT = ["bodyweight", "dumbbells", "barbell", "machine"]
LEVELS = ["beginner", "intermediate", "advanced"]

# ---------------------------------------------------------------------------
# Exercise database: name, primary muscles, secondary muscles, equipment,
# level, suggested sets x reps, and a short form tip.
# ---------------------------------------------------------------------------
def ex(name, primary, secondary, equipment, level, rx, tip):
    return dict(name=name, primary=primary, secondary=secondary,
                equipment=equipment, level=level, rx=rx, tip=tip)

COMPOUND, ISO, CORE = "3-4 x 6-10", "3 x 10-15", "3 x 30-45 s or 12-20 reps"

EXERCISES = [
    # Chest
    ex("Push-up", ["chest"], ["triceps", "shoulders", "abs"], "bodyweight", "beginner", "3 x 8-15", "Keep your body in one straight line; lower until your chest nearly touches the floor."),
    ex("Incline push-up (hands on a bench)", ["chest"], ["triceps", "shoulders"], "bodyweight", "beginner", "3 x 10-15", "An easier push-up variation, good for building up to full push-ups."),
    ex("Decline push-up (feet elevated)", ["chest", "shoulders"], ["triceps"], "bodyweight", "intermediate", "3 x 8-12", "Hits the upper chest harder; don't let your hips sag."),
    ex("Dumbbell bench press", ["chest"], ["triceps", "shoulders"], "dumbbells", "beginner", COMPOUND, "Lower with control until elbows are just below the bench, then press up and slightly in."),
    ex("Incline dumbbell press", ["chest"], ["shoulders", "triceps"], "dumbbells", "intermediate", COMPOUND, "Set the bench around 30 degrees to target the upper chest."),
    ex("Dumbbell fly", ["chest"], [], "dumbbells", "intermediate", ISO, "Slight bend in the elbows; stretch the chest, don't go lower than comfortable."),
    ex("Barbell bench press", ["chest"], ["triceps", "shoulders"], "barbell", "intermediate", COMPOUND, "Shoulder blades pinched back, feet planted; use a spotter for heavy sets."),
    ex("Cable / machine chest fly", ["chest"], [], "machine", "beginner", ISO, "Squeeze the handles together and pause for a second."),
    ex("Chest press machine", ["chest"], ["triceps", "shoulders"], "machine", "beginner", COMPOUND, "A safe way to learn the pressing pattern."),

    # Back
    ex("Superman hold", ["lower back"], ["glutes", "back"], "bodyweight", "beginner", "3 x 20-30 s", "Lift arms and legs a few centimetres; don't crank your neck up."),
    ex("Inverted row (under a sturdy table or bar)", ["back"], ["biceps", "forearms"], "bodyweight", "beginner", "3 x 8-12", "Pull your chest to the bar and keep your body rigid."),
    ex("Pull-up", ["back"], ["biceps", "forearms"], "bodyweight", "advanced", "3-4 x 5-10", "Start from a dead hang and pull your chest toward the bar."),
    ex("Chin-up", ["back", "biceps"], ["forearms"], "bodyweight", "intermediate", "3-4 x 5-10", "Palms facing you; a bit more biceps than pull-ups."),
    ex("One-arm dumbbell row", ["back"], ["biceps", "forearms"], "dumbbells", "beginner", COMPOUND, "Drive the elbow back toward your hip, don't twist your torso."),
    ex("Renegade row", ["back"], ["abs", "obliques", "shoulders"], "dumbbells", "advanced", "3 x 6-10 per side", "Wide feet for stability and hips as still as possible."),
    ex("Barbell bent-over row", ["back"], ["biceps", "lower back", "forearms"], "barbell", "intermediate", COMPOUND, "Hinge forward with a flat back and pull the bar to your lower ribs."),
    ex("Deadlift", ["back", "hamstrings", "glutes"], ["lower back", "forearms", "quads"], "barbell", "advanced", "3-4 x 3-6", "Bar over mid-foot, push the floor away and keep it close to your legs."),
    ex("Lat pulldown", ["back"], ["biceps"], "machine", "beginner", COMPOUND, "Pull the bar to your upper chest, leading with the elbows."),
    ex("Seated cable row", ["back"], ["biceps"], "machine", "beginner", COMPOUND, "Sit tall and squeeze your shoulder blades together at the end."),

    # Shoulders
    ex("Pike push-up", ["shoulders"], ["triceps", "chest"], "bodyweight", "intermediate", "3 x 6-12", "Hips high in an upside-down V; lower the top of your head toward the floor."),
    ex("Dumbbell shoulder press", ["shoulders"], ["triceps"], "dumbbells", "beginner", COMPOUND, "Press straight up without leaning back."),
    ex("Lateral raise", ["shoulders"], [], "dumbbells", "beginner", ISO, "Lead with the elbows to about shoulder height and use light weight."),
    ex("Rear-delt fly", ["shoulders", "back"], [], "dumbbells", "intermediate", ISO, "Hinge forward, open arms like wings and keep the neck relaxed."),
    ex("Barbell overhead press", ["shoulders"], ["triceps", "abs"], "barbell", "intermediate", COMPOUND, "Squeeze your glutes and ribs down so you don't arch your back."),
    ex("Shoulder press machine", ["shoulders"], ["triceps"], "machine", "beginner", COMPOUND, "Adjust the seat so the handles start at shoulder level."),
    ex("Face pull (cable)", ["shoulders", "back"], [], "machine", "beginner", ISO, "Pull to your forehead, elbows high, great for posture."),

    # Biceps
    ex("Dumbbell curl", ["biceps"], ["forearms"], "dumbbells", "beginner", ISO, "Elbows pinned to your sides; no swinging."),
    ex("Hammer curl", ["biceps", "forearms"], [], "dumbbells", "beginner", ISO, "Neutral grip builds the brachialis and forearms too."),
    ex("Incline dumbbell curl", ["biceps"], [], "dumbbells", "intermediate", ISO, "The stretch at the bottom is where this one earns its keep."),
    ex("Barbell curl", ["biceps"], ["forearms"], "barbell", "beginner", ISO, "Stand tall and curl without rocking your torso."),
    ex("Cable curl", ["biceps"], [], "machine", "beginner", ISO, "Constant tension through the whole range."),

    # Triceps
    ex("Bench dips", ["triceps"], ["chest", "shoulders"], "bodyweight", "beginner", "3 x 8-15", "Keep your back close to the bench and don't sink too deep."),
    ex("Diamond push-up", ["triceps"], ["chest", "shoulders"], "bodyweight", "intermediate", "3 x 6-12", "Hands close together under your chest; elbows tucked."),
    ex("Overhead dumbbell extension", ["triceps"], [], "dumbbells", "beginner", ISO, "Keep your upper arms close to your head."),
    ex("Dumbbell kickback", ["triceps"], [], "dumbbells", "beginner", ISO, "Upper arm parallel to the floor; straighten fully and squeeze."),
    ex("Close-grip bench press", ["triceps"], ["chest", "shoulders"], "barbell", "intermediate", COMPOUND, "Hands about shoulder-width, elbows tucked."),
    ex("Cable triceps pushdown", ["triceps"], [], "machine", "beginner", ISO, "Elbows stay at your sides; lock out at the bottom."),

    # Forearms
    ex("Dead hang", ["forearms"], ["back", "shoulders"], "bodyweight", "beginner", "3 x 20-45 s", "Great grip work; relax your shoulders away from your ears."),
    ex("Wrist curl", ["forearms"], [], "dumbbells", "beginner", "3 x 15-20", "Rest forearms on your thighs and curl only the wrist."),
    ex("Farmer's carry", ["forearms"], ["abs", "shoulders", "back"], "dumbbells", "beginner", "3 x 30-40 m", "Walk tall with heavy dumbbells and don't lean."),

    # Abs / obliques / lower back
    ex("Plank", ["abs"], ["shoulders", "obliques", "glutes"], "bodyweight", "beginner", CORE, "Squeeze glutes and pull ribs down; no sagging hips."),
    ex("Dead bug", ["abs"], [], "bodyweight", "beginner", "3 x 8-12 per side", "Press your lower back to the floor as you extend opposite arm and leg."),
    ex("Bicycle crunch", ["abs", "obliques"], [], "bodyweight", "beginner", "3 x 15-20", "Slow, rotate from the ribs and don't pull on your neck."),
    ex("Hanging knee raise", ["abs"], ["forearms"], "bodyweight", "intermediate", "3 x 8-15", "Curl your pelvis up instead of just swinging your legs."),
    ex("Hanging leg raise", ["abs"], ["forearms"], "bodyweight", "advanced", "3 x 6-12", "Straight legs and a controlled lowering."),
    ex("Side plank", ["obliques"], ["abs", "shoulders", "glutes"], "bodyweight", "beginner", "3 x 20-40 s per side", "Stack your feet and push the floor away."),
    ex("Russian twist", ["obliques", "abs"], [], "dumbbells", "intermediate", "3 x 12-20", "Rotate your ribcage, not just your arms."),
    ex("Cable woodchop", ["obliques"], ["abs", "shoulders"], "machine", "intermediate", "3 x 10-12 per side", "Pivot through your feet and keep your arms long."),
    ex("Ab wheel rollout", ["abs"], ["shoulders", "lower back"], "bodyweight", "advanced", "3 x 6-10", "Only roll as far as you can keep your back from arching."),
    ex("Bird dog", ["lower back"], ["glutes", "abs"], "bodyweight", "beginner", "3 x 8-12 per side", "Move slowly and keep your hips level."),
    ex("Back extension", ["lower back"], ["glutes", "hamstrings"], "machine", "beginner", "3 x 10-15", "Raise to a straight line, not an overarch."),
    ex("Good morning", ["lower back", "hamstrings"], ["glutes"], "barbell", "advanced", "3 x 8-10", "Hinge at the hips with a flat back and light weight."),

    # Legs
    ex("Bodyweight squat", ["quads", "glutes"], ["hamstrings", "calves"], "bodyweight", "beginner", "3 x 12-20", "Sit between your hips, chest up, heels down."),
    ex("Reverse lunge", ["quads", "glutes"], ["hamstrings"], "bodyweight", "beginner", "3 x 8-12 per leg", "Step back, drop the back knee toward the floor and drive through the front heel."),
    ex("Bulgarian split squat", ["quads", "glutes"], ["hamstrings"], "bodyweight", "intermediate", "3 x 8-12 per leg", "Back foot on a bench; lean slightly forward to bring in the glutes."),
    ex("Pistol squat (assisted)", ["quads", "glutes"], ["abs"], "bodyweight", "advanced", "3 x 3-6 per leg", "Hold a doorframe at first and control the descent."),
    ex("Wall sit", ["quads"], ["glutes"], "bodyweight", "beginner", "3 x 30-60 s", "Thighs parallel to the floor and back flat on the wall."),
    ex("Goblet squat", ["quads", "glutes"], ["abs"], "dumbbells", "beginner", COMPOUND, "Hold one dumbbell at your chest; great for learning squat depth."),
    ex("Dumbbell Romanian deadlift", ["hamstrings", "glutes"], ["lower back", "forearms"], "dumbbells", "beginner", COMPOUND, "Push hips back with soft knees until you feel a hamstring stretch."),
    ex("Walking lunge", ["quads", "glutes"], ["hamstrings", "calves"], "dumbbells", "intermediate", "3 x 10-12 per leg", "Take long steps and keep your torso upright."),
    ex("Barbell back squat", ["quads", "glutes"], ["hamstrings", "lower back", "abs"], "barbell", "intermediate", COMPOUND, "Brace your core, break at hips and knees together, and use safety bars."),
    ex("Barbell hip thrust", ["glutes"], ["hamstrings"], "barbell", "intermediate", COMPOUND, "Chin tucked, shins vertical at the top, squeeze hard."),
    ex("Glute bridge", ["glutes"], ["hamstrings", "lower back"], "bodyweight", "beginner", "3 x 12-20", "Drive through your heels and don't over-arch at the top."),
    ex("Single-leg glute bridge", ["glutes", "hamstrings"], [], "bodyweight", "intermediate", "3 x 8-12 per leg", "Keep hips level as you lift."),
    ex("Nordic hamstring curl", ["hamstrings"], ["glutes"], "bodyweight", "advanced", "3 x 3-6", "Anchor your heels and lower as slowly as you can."),
    ex("Leg press", ["quads", "glutes"], ["hamstrings"], "machine", "beginner", COMPOUND, "Don't let your lower back round off the pad."),
    ex("Leg extension", ["quads"], [], "machine", "beginner", ISO, "Pause and squeeze at the top."),
    ex("Lying leg curl", ["hamstrings"], ["calves"], "machine", "beginner", ISO, "Slow lowering; keep your hips down."),
    ex("Hip abduction machine", ["glutes"], [], "machine", "beginner", ISO, "Slow reps; avoid bouncing."),

    # Calves
    ex("Standing calf raise", ["calves"], [], "bodyweight", "beginner", "3 x 15-25", "Pause at the top and get a full stretch at the bottom."),
    ex("Single-leg calf raise", ["calves"], [], "bodyweight", "intermediate", "3 x 10-15 per leg", "Hold a wall for balance."),
    ex("Dumbbell calf raise", ["calves"], [], "dumbbells", "beginner", "3 x 12-20", "Stand on a step edge for a bigger range."),
    ex("Seated calf raise machine", ["calves"], [], "machine", "beginner", "3 x 12-20", "Slow, full-range reps."),
]

# ---------------------------------------------------------------------------
# Free-text understanding: map words people actually type to muscle groups.
# ---------------------------------------------------------------------------
ALL_MAIN = ["chest", "back", "shoulders", "biceps", "triceps", "abs",
            "quads", "hamstrings", "glutes", "calves"]

KEYWORDS = [  # checked in order; longer phrases first
    ("full body|whole body|total body|everything|all over", ALL_MAIN),
    ("upper body|upper-body", ["chest", "back", "shoulders", "biceps", "triceps"]),
    ("lower body|lower-body", ["quads", "hamstrings", "glutes", "calves"]),
    ("lower back|low back|spine", ["lower back"]),
    ("six pack|six-pack|sixpack|stomach|belly|abdominal|abdominals|abdomen|core|abs?",
     ["abs", "obliques", "lower back"]),
    ("love handles?|obliques?", ["obliques"]),
    ("push", ["chest", "shoulders", "triceps"]),
    ("pull", ["back", "biceps"]),
    ("chest|pecs?|pectorals?", ["chest"]),
    ("back|lats?|traps?|rhomboids?", ["back"]),
    ("shoulders?|delts?|deltoids?", ["shoulders"]),
    ("biceps?", ["biceps"]),
    ("triceps?", ["triceps"]),
    ("arms?", ["biceps", "triceps", "forearms"]),
    ("forearms?|grip|wrists?", ["forearms"]),
    ("legs?", ["quads", "hamstrings", "glutes", "calves"]),
    ("quads?|quadriceps|thighs?", ["quads"]),
    ("hamstrings?", ["hamstrings"]),
    ("glutes?|butt|booty|bum", ["glutes"]),
    ("calf|calves", ["calves"]),
]


def parse_muscles(text):
    """Turn free text like 'chest, triceps and a stronger core' into muscle names."""
    text = (text or "").lower()
    found = set()
    for pattern, muscles in KEYWORDS:
        regex = re.compile(r"\b(?:%s)\b" % pattern)
        if regex.search(text):
            found.update(muscles)
            text = regex.sub(" ", text)  # so 'lower back' doesn't also trigger 'back'
    return [m for m in MUSCLES if m in found]


def suggest(muscles, equipment, level, per_group=4):
    max_level = LEVELS.index(level)
    allowed = set(equipment) | {"bodyweight"}
    seen, groups = set(), []
    for muscle in muscles:
        pool = [e for e in EXERCISES
                if e["equipment"] in allowed and LEVELS.index(e["level"]) <= max_level]
        primary = [e for e in pool if muscle in e["primary"]]
        secondary = [e for e in pool if muscle in e["secondary"] and muscle not in e["primary"]]
        # Prefer lead exercises where this muscle is the main target, easiest first.
        primary.sort(key=lambda e: (-(len(e["primary"]) == 1), LEVELS.index(e["level"])))
        # Avoid repeating the same exercise across groups when there's a fresh option,
        # but fall back to repeats before settling for weak secondary movers.
        fresh = [e for e in primary if e["name"] not in seen]
        repeats = [e for e in primary if e["name"] in seen]
        picks = (fresh + repeats)[:per_group]
        if len(picks) < 3:
            extra = [e for e in secondary if e["name"] not in seen] + \
                    [e for e in secondary if e["name"] in seen]
            picks += extra[: 3 - len(picks)]
        seen.update(e["name"] for e in picks)
        groups.append({"muscle": muscle, "exercises": picks})
    return groups


@app.route("/")
def index():
    return render_template_string(PAGE, muscles=MUSCLES,
                                  equipment=EQUIPMENT, levels=LEVELS)


@app.route("/api/suggest", methods=["POST"])
def api_suggest():
    data = request.get_json(silent=True) or {}
    chips = [m for m in data.get("chips", []) if m in MUSCLES]
    muscles = list(dict.fromkeys(parse_muscles(data.get("text", "")) + chips))
    muscles = [m for m in MUSCLES if m in muscles]

    equipment = [e for e in data.get("equipment", EQUIPMENT) if e in EQUIPMENT]
    level = data.get("level") if data.get("level") in LEVELS else "intermediate"

    if not muscles:
        return jsonify(recognized=[], groups=[],
                       message="I couldn't spot a body part there. Try words like "
                               "'chest', 'legs', 'core', 'arms' or tap a chip.")
    return jsonify(recognized=muscles, groups=suggest(muscles, equipment, level))


if __name__ == "__main__":
    app.run(debug=True)
 
 
 