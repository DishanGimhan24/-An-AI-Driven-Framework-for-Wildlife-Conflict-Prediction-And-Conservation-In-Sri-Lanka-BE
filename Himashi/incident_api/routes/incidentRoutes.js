const express = require("express");
const Incident = require("../models/Incident");

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    const incidents = await Incident.find().sort({ createdAt: -1 });
    res.json(incidents);
  } catch (error) {
    res.status(500).json({ message: "Failed to fetch incidents." });
  }
});

router.post("/", async (req, res) => {
  try {
    const incident = await Incident.create(req.body);
    res.status(201).json(incident);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

module.exports = router;
