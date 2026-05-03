const mongoose = require("mongoose");

const IncidentSchema = new mongoose.Schema(
  {
    province: { type: String, required: true, trim: true },
    district: { type: String, required: true, trim: true },
    villageArea: { type: String, required: true, trim: true },
    roadRailway: { type: String, required: true, trim: true },
    nearestLandmark: { type: String, required: true, trim: true },
    incidentDate: { type: Date, required: true },
    incidentTime: { type: String, required: true },
    dayNight: { type: String, required: true, enum: ["Day", "Night"] },
    animalType: { type: String, required: true, trim: true },
    animalCount: { type: Number, required: true, min: 1 },
    animalAge: { type: String, trim: true },
    vehicleType: { type: String, required: true, trim: true },
    direction: { type: String, required: true, trim: true },
    injuryAnimal: { type: String, required: true, trim: true },
    deathAnimal: { type: String, required: true, trim: true },
    injuryHumans: { type: String, required: true, trim: true },
    deathHumans: { type: String, required: true, trim: true },
    description: { type: String, required: true, trim: true }
  },
  { timestamps: true }
);

module.exports = mongoose.model("Incident", IncidentSchema);
