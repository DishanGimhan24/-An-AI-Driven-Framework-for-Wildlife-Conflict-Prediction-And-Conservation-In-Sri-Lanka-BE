const express = require("express");
const Incident = require("../models/Incident");

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    const incidents = await Incident.find().sort({ createdAt: -1 });
    res.json(incidents);
  } catch (error) {
    res.status(500).json({ message: "Failed to fetch incidents" });
  }
});

router.post("/add", async (req, res) => {
  try {
    const incident = new Incident(req.body);
    await incident.save();
    res.status(201).json({ message: "Incident saved successfully" });
  } catch (error) {
    res.status(500).json({ message: "Failed to save incident" });
  }
});

module.exports = router;
