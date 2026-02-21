/**
 * Mock analysis data for frontend development.
 * Matches the shape your backend will eventually return.
 */
export const mockAnalysis = {
  status: "success",
  ref_path: "uploads/reference/sample.mp4",
  prac_path: "uploads/practice/sample.mp4",
  analysis: {
    overallScore: 78,
    moves: [
      {
        id: 1,
        timestamp: "0:05",
        label: "Arm extension",
        match: false,
        feedback: "Your arms were lower than the reference.",
        tips: ["Extend fully through the fingertips", "Sync with the beat on count 3"],
      },
      {
        id: 2,
        timestamp: "0:12",
        label: "Hip sway",
        match: true,
        feedback: null,
        tips: [],
      },
      {
        id: 3,
        timestamp: "0:18",
        label: "Shoulder roll",
        match: false,
        feedback: "The roll was faster than the reference. Try to sustain the movement.",
        tips: ["Count 4 beats for the full roll", "Lead with your chest"],
      },
      {
        id: 4,
        timestamp: "0:25",
        label: "Foot placement",
        match: false,
        feedback: "Your left foot was too wide on the pivot.",
        tips: ["Keep feet shoulder-width", "Pivot on the ball of your foot"],
      },
    ],
  },
};
