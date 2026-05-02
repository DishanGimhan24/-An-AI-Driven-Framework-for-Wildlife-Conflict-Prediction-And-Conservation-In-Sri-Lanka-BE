const mongoose = require("mongoose");

const IncidentSchema = new mongoose.Schema(
  {
    province: { type: String, trim: true },
    district: { type: String, trim: true },
    village: { type: String, trim: true },
    road: { type: String, trim: true },
    landmark: { type: String, trim: true },
    date: { type: Date },
    time: { type: String, trim: true },
    dayNight: { type: String, trim: true },
    animalType: { type: String, trim: true },
    numberOfAnimals: { type: Number },
    age: { type: String, trim: true },
    vehicleType: { type: String, trim: true },
    direction: { type: String, trim: true },
    injuryAnimal: { type: String, trim: true },
    deathAnimal: { type: String, trim: true },
    injuryHuman: { type: String, trim: true },
    deathHuman: { type: String, trim: true },
    description: { type: String, trim: true }
  },
  { timestamps: true }
);

module.exports = mongoose.model("Incident", IncidentSchema);
