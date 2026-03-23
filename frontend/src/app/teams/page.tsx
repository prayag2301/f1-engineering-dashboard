"use client";

type OfficialTeam2026 = {
  name: string;
  fullName: string;
  drivers: [string, string];
  powerUnit: string;
  base: string;
  carImageUrl: string;
};

const OFFICIAL_2026_TEAMS: OfficialTeam2026[] = [
  {
    name: "Alpine",
    fullName: "BWT Alpine F1 Team",
    drivers: ["Pierre Gasly", "Franco Colapinto"],
    powerUnit: "Mercedes",
    base: "Enstone, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/alpine/2025alpinecarright.webp",
  },
  {
    name: "Aston Martin",
    fullName: "Aston Martin Aramco Formula One Team",
    drivers: ["Fernando Alonso", "Lance Stroll"],
    powerUnit: "Honda RBPT",
    base: "Silverstone, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/astonmartin/2025astonmartincarright.webp",
  },
  {
    name: "Audi",
    fullName: "Audi Revolut F1 Team",
    drivers: ["Nico Hulkenberg", "Gabriel Bortoleto"],
    powerUnit: "Audi",
    base: "Hinwil, Switzerland",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/audi/2026audicarright.webp",
  },
  {
    name: "Cadillac",
    fullName: "Cadillac Formula 1 Team",
    drivers: ["Sergio Perez", "Valtteri Bottas"],
    powerUnit: "Ferrari",
    base: "Silverstone, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/cadillac/2026cadillaccarright.webp",
  },
  {
    name: "Ferrari",
    fullName: "Scuderia Ferrari",
    drivers: ["Charles Leclerc", "Lewis Hamilton"],
    powerUnit: "Ferrari",
    base: "Maranello, Italy",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/ferrari/2025ferraricarright.webp",
  },
  {
    name: "Haas F1 Team",
    fullName: "TGR Haas F1 Team",
    drivers: ["Esteban Ocon", "Oliver Bearman"],
    powerUnit: "Ferrari",
    base: "Kannapolis, USA",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/haas/2025haascarright.webp",
  },
  {
    name: "McLaren",
    fullName: "McLaren F1 Team",
    drivers: ["Lando Norris", "Oscar Piastri"],
    powerUnit: "Mercedes",
    base: "Woking, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/mclaren/2025mclarencarright.webp",
  },
  {
    name: "Mercedes",
    fullName: "Mercedes-AMG Petronas F1 Team",
    drivers: ["George Russell", "Kimi Antonelli"],
    powerUnit: "Mercedes",
    base: "Brackley, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/mercedes/2025mercedescarright.webp",
  },
  {
    name: "Racing Bulls",
    fullName: "Visa Cash App Racing Bulls Formula One Team",
    drivers: ["Liam Lawson", "Arvid Lindblad"],
    powerUnit: "Red Bull Ford Powertrains",
    base: "Faenza, Italy",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/racingbulls/2025racingbullscarright.webp",
  },
  {
    name: "Red Bull Racing",
    fullName: "Oracle Red Bull Racing",
    drivers: ["Max Verstappen", "Isack Hadjar"],
    powerUnit: "Red Bull Ford Powertrains",
    base: "Milton Keynes, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/redbullracing/2025redbullracingcarright.webp",
  },
  {
    name: "Williams",
    fullName: "Williams Racing",
    drivers: ["Carlos Sainz", "Alexander Albon"],
    powerUnit: "Mercedes",
    base: "Grove, UK",
    carImageUrl:
      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/williams/2025williamscarright.webp",
  },
];

export default function TeamsPage() {
  return (
    <>
      <h1 className="page-title">Teams</h1>
      <p className="page-subtitle">
        Official 2026 F1 Constructor Grid (updated February 19, 2026)
      </p>

      <div className="upgrade-grid">
        {OFFICIAL_2026_TEAMS.map((team) => (
          <div key={team.name} className="card">
            <div className="card__car">
              <img
                src={team.carImageUrl}
                alt={`${team.name} official car image`}
                loading="lazy"
                className="card__car-image"
                onError={(event) => {
                  const target = event.currentTarget;
                  target.style.display = "none";
                }}
              />
            </div>
            <div className="card__header">
              <span className="card__team">{team.name}</span>
              <span className="card__race">{team.powerUnit}</span>
            </div>
            <div className="card__component">{team.fullName}</div>
            <div className="card__meta">
              <span className="badge badge--confidence">{team.base}</span>
              {team.drivers.map((driver) => (
                <span
                  key={`${team.name}-${driver}`}
                  className="badge badge--confidence"
                >
                  {driver}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
