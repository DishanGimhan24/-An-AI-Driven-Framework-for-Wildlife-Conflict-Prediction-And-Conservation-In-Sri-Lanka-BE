const express = require("express");
const cors = require("cors");
const path = require("path");
const dotenv = require("dotenv");
const connectDB = require("./config/db");
const incidentRoutes = require("./routes/incidentRoutes");

const envConfig = dotenv.config({ path: path.join(__dirname, ".env") });

if (envConfig.error) {
  dotenv.config({ path: path.join(__dirname, "routes", ".env") });
}

const app = express();

app.use(
  cors({
    origin: "*",
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);
app.options("*", cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.json({ status: "incident api running" });
});

app.use("/api/incidents", incidentRoutes);

const startServer = async () => {
  await connectDB();

  const PORT = process.env.PORT || 5000;
  app.listen(PORT, () => {
    console.log(`Incident API listening on port ${PORT}`);
  });
};

startServer().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
