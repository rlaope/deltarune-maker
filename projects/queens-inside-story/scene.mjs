// The service wing encounter. Timings are seconds, and positions are logical pixels.
export const encounter = {
  duration: 60,
  field: {
    kris: { x: 76, y: 210 },
    susie: { x: 47, y: 210 },
    queen: { x: 510, y: 116 },
    block: { x: 157, y: 210 },
    switch: { x: 392, y: 145 },
  },
  battle: {
    starts: [{ x: 83, y: 153 }, { x: 113, y: 213 }],
    hp: [42, 48],
    queen: { x: 309, y: 157 },
    queenHp: 74,
    tellDuration: 0.76,
    // Each attack is [tell time, hero index, projectile, flight time].
    waves: [
      { duration: 12.20, attacks: [
        [0.60, 0, 'laser', 0.82], [2.72, 1, 'laser', 0.68],
        [4.75, 0, 'battery', 0.80], [6.70, 1, 'battery', 0.72],
        [9.02, 0, 'laser', 0.68], [9.43, 1, 'laser', 0.67],
      ] },
      { duration: 11.25, attacks: [
        [0.48, 1, 'laser', 0.53], [1.04, 0, 'battery', 0.58],
        [2.49, 0, 'laser', 0.55], [2.49, 1, 'laser', 0.55],
        [4.36, 1, 'battery', 0.61], [4.91, 0, 'laser', 0.48],
        [6.47, 0, 'battery', 0.57], [7.03, 1, 'laser', 0.46],
        [8.21, 0, 'laser', 0.48], [8.73, 1, 'battery', 0.54],
        [9.35, 0, 'laser', 0.51],
      ] },
    ],
  },
  dialogue: {
    meeting: [
      { speaker: 'queen', text: 'Ohohoho! Welcome To My Optional Security Check.' },
      { speaker: 'susie', text: 'Then why did you lock the door?' },
      { speaker: 'queen', text: 'It Is Optional For Me.' },
      { speaker: 'susie', text: 'Sounds pretty mandatory.' },
    ],
    fieldReward: { speaker: 'susie', text: "Dibs. Unless it grows legs." },
    power: { speaker: 'susie', text: 'Kris. That opened something.' },
    battleEntry: { speaker: 'susie', text: "Let's go!" },
    victory: { speaker: 'queen', text: 'I Have Opted Out Of My Own Test.' },
    defeat: { speaker: 'queen', text: 'I Offer Unlimited Retakes.' },
  },
};
