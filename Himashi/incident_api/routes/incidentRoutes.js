const express = require("express");
const mongoose = require("mongoose");
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

router.post("/add", async (req, res) => {
  try {
    const incident = await Incident.create(req.body);
    res.status(201).json(incident);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;

    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ message: "Invalid incident ID." });
    }

    const incident = await Incident.findById(id);

    if (!incident) {
      return res.status(404).json({ message: "Incident not found." });
    }

    return res.json(incident);
  } catch (error) {
    return res.status(500).json({ message: "Failed to fetch incident." });
  }
});

const updateIncident = async (req, res) => {
  try {
    const { id } = req.params;

    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ message: "Invalid incident ID." });
    }

    const updatedIncident = await Incident.findByIdAndUpdate(id, req.body, {
      new: true,
      runValidators: true
    });

    if (!updatedIncident) {
      return res.status(404).json({ message: "Incident not found." });
    }

    return res.json(updatedIncident);
  } catch (error) {
    return res.status(400).json({ message: error.message });
  }
};

router.put("/:id", updateIncident);
// router.patch("/:id", updateIncident);

router.delete("/:id", async (req, res) => {
  try {
    const { id } = req.params;

    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ message: "Invalid incident ID." });
    }

    const deletedIncident = await Incident.findByIdAndDelete(id);

    if (!deletedIncident) {
      return res.status(404).json({ message: "Incident not found." });
    }

    return res.json({ message: "Incident deleted successfully.", incident: deletedIncident });
  } catch (error) {
    return res.status(500).json({ message: "Failed to delete incident." });
  }
});

module.exports = router;
