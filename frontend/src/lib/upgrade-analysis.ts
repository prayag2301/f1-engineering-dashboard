// Browser-side interpretation of the original analyzer's component vocabulary.
// This is a reading aid, not evidence validation or a performance model.
const zones = [
  {
    label: "Front wing",
    category: "Aerodynamics",
    terms: ["front wing", "outwash", "endplate"],
    intent:
      "Front-wing changes can alter front load and the flow reaching the wheels and floor.",
    check:
      "Compare front balance and downstream flow at matched ride height, steering angle and speed.",
  },
  {
    label: "Rear wing",
    category: "Aerodynamics",
    terms: ["rear wing", "beam wing", "drs", "gurney"],
    intent:
      "Rear-wing changes can shift the balance between rear aerodynamic load and drag.",
    check:
      "Compare straight-line speed and rear balance at the same wing setting, deployment and fuel load.",
  },
  {
    label: "Floor edge",
    category: "Floor",
    terms: ["floor edge", "edge wing", "edge profile"],
    intent:
      "Floor-edge geometry can change the flow structures along the underfloor boundary.",
    check:
      "Check whether the effect persists across ride-height and yaw changes, rather than only one operating point.",
  },
  {
    label: "Floor & diffuser",
    category: "Floor",
    terms: ["floor", "underfloor", "diffuser", "tunnel", "ground effect"],
    intent:
      "Underfloor and diffuser revisions can alter pressure distribution and the sensitivity of aerodynamic load to the car's attitude.",
    check:
      "Compare load and balance through matched medium- and high-speed conditions, with ride-height data.",
  },
  {
    label: "Suspension",
    category: "Mechanical",
    terms: [
      "suspension",
      "wishbone",
      "pushrod",
      "pullrod",
      "anti-dive",
      "anti-squat",
      "damper",
    ],
    intent:
      "Suspension changes may affect platform control or airflow around the arms. A fairing change alone does not establish a change to the kinematics.",
    check:
      "Identify whether hardpoints, springing or only the exterior fairing changed before inferring a mechanical effect.",
  },
  {
    label: "Sidepods & cooling",
    category: "Cooling",
    terms: ["sidepod", "inlet", "radiator", "cooling", "louvre", "thermal"],
    intent:
      "Inlet and sidepod changes can affect cooling flow and the external flow path toward the rear of the car.",
    check:
      "Compare cooling demand and temperatures alongside drag and aerodynamic balance.",
  },
  {
    label: "Engine cover",
    category: "Bodywork",
    terms: ["engine cover", "airbox", "spine", "bodywork"],
    intent:
      "Engine-cover surfaces can change the flow around the rear bodywork; outlets can also change cooling capacity.",
    check:
      "Establish the visible geometry and cooling configuration before attributing an aerodynamic benefit.",
  },
  {
    label: "Brake ducts",
    category: "Cooling",
    terms: ["brake duct", "brake cooling"],
    intent:
      "Brake-duct revisions may change cooling flow and the airflow around the wheel assembly.",
    check:
      "Compare brake temperatures and cooling requirements under comparable braking loads.",
  },
  {
    label: "Nose",
    category: "Aerodynamics",
    terms: ["nose", "nosecone"],
    intent:
      "Nose geometry helps define the flow approaching the central front-wing and chassis region.",
    check:
      "Inspect the wing attachment and visible cross-section; a livery line alone may not mark a geometric change.",
  },
  {
    label: "Power unit",
    category: "Power unit",
    terms: ["power unit", "turbo", "ers", "energy store", "combustion"],
    intent:
      "Power-unit claims may concern output, energy deployment or thermal management; exterior geometry cannot establish those changes.",
    check:
      "Look for direct technical documentation and comparable deployment or power data.",
  },
];

function matches(text: string, term: string) {
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`\\b${escaped}s?\\b`, "i").test(text);
}

export function analyzeDescription(description: string, detail: string) {
  const text = `${description} ${detail}`;
  return zones
    .map((zone) => ({
      ...zone,
      signals: zone.terms.filter((term) => matches(text, term)),
    }))
    .filter((zone) => zone.signals.length > 0)
    .sort(
      (a, b) =>
        Math.max(...b.signals.map((s) => s.length)) -
        Math.max(...a.signals.map((s) => s.length)),
    );
}
