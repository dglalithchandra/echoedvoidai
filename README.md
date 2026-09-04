   # EchoedVoidAI

   AI-powered automated underwater marine debris and anomaly detection
   system using side-scan sonar imagery.

   ## What this is
   An end-to-end pipeline that ingests side-scan sonar logs, detects and
   classifies man-made debris against natural seafloor clutter, and outputs
   geotagged, confidence-scored reports through a dashboard.

   ## Classes
   | ID | Class | Covers |
   |---|---|---|
   | 0 | net | Entangled fishing gear, ropes, lines, traps/pots |
   | 1 | pipe | Pipelines, cables, hoses |
   | 2 | drum | Barrels, tanks, containers |
   | 3 | wreck | Shipwrecks, large debris fields |
   | 4 | small_debris | Bottles, cans, tires, valves, hooks, propellers (merged) |
   | 5 | unknown | Anomaly catch-all — flagged as man-made-likely, doesn't match 1–5 |

   ## Structure
