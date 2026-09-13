<div align="center">

# 🛰️ Aegis

**Autonomous multi-agent orbital collision de-confliction.**

[![Built at Bit N Build](https://img.shields.io/badge/Bit%20N%20Build-Around%20the%20World%202026-3b82f6?style=flat-square)](#team)
[![Built in 24 hours](https://img.shields.io/badge/built%20in-24%20hours-f59e0b?style=flat-square)]()

<p>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic">
<img src="https://img.shields.io/badge/WebSockets-3b82f6?style=for-the-badge&logo=socketdotio&logoColor=white" alt="WebSockets">
<br>
<img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
<img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
<img src="https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS">
<br>
<img src="https://img.shields.io/badge/SGP4-orbital%20propagation-1e3a5f?style=for-the-badge" alt="SGP4">
<img src="https://img.shields.io/badge/react--globe.gl-3D%20globe-143120?style=for-the-badge" alt="react-globe.gl">
<img src="https://img.shields.io/badge/CelesTrak-TLE%20data-3a2e0f?style=for-the-badge" alt="CelesTrak">
</p>

Aegis replaces the manual, email-based satellite collision-avoidance process with autonomous negotiation agents — one per satellite operator — that detect a real conjunction event, negotiate who maneuvers using real orbital physics and mission-priority data, and produce a fully auditable resolution.

*No standardized automated protocol exists for this today. Aegis is a working demonstration of what one could look like.*

</div>

---

## The Problem

When two satellites from different operators are on a collision course, resolution today happens through **manual emails between engineers** — a real, documented bottleneck (e.g. the 2019 SpaceX/ESA Starlink–Aeolus incident). As LEO gets more crowded, this doesn't scale.

## What Aegis Does

| Step | Description |
|---|---|
| **1. Detect** | Finds a real close-approach conjunction from live/cached CelesTrak TLE data, propagated with SGP4. |
| **2. Negotiate** | Two autonomous operator agents reason over mission priority and fuel cost, exchange proposals over multiple rounds, and converge on who maneuvers. The `yield_score` that actually decides the outcome always comes from deterministic Python — the LLM only narrates it in plain language. |
| **3. Validate** | A third agent re-propagates the proposed maneuver 6 hours forward to confirm it doesn't create a *new* collision risk before approving it. It can also honestly report "no safe maneuver found." |
| **4. Visualize** | A live 3D globe shows the conjunction, the negotiation as it happens, and the resulting trajectory change. |

---

## Screenshots

| Live Orbital View | Negotiation Console & Result |
|:---:|:---:|
| ![Monitor](docs/screenshots/Monitor2.jpeg) | ![Conjunction Resolution Desk](docs/screenshots/Conjunction_Resolution_Desk.jpeg) |

<p align="center"><img src="docs/screenshots/Resolution_archive.jpeg" alt="Resolution Archive" width="80%"></p>

---

## Architecture

```mermaid
flowchart TD
    CT[("🛰️ CelesTrak<br/>TLE data")] -->|"1 · fetch + cache"| MON
 
    MON["Monitor Agent<br/><i>sgp4 propagation, deterministic</i>"] -->|"2-3 · ConjunctionAlert"| ORCH
 
    ORCH{{"Orchestrator<br/><i>session state · sequencing · WebSocket broadcast</i>"}}
 
    ORCH -->|"4 · creates NegotiationSession"| OA["Operator Agent A<br/><i>yield_score: cost_functions.py</i><br/><i>justification: Claude narration</i>"]
    ORCH -->|"4 · creates NegotiationSession"| OB["Operator Agent B<br/><i>yield_score: cost_functions.py</i><br/><i>justification: Claude narration</i>"]
 
    OA <-->|"proposals / counter-proposals"| OB
    OA -->|"6 · NegotiationMessage"| ORCH
    OB -->|"6 · NegotiationMessage"| ORCH
 
    ORCH -->|"7 · on convergence or round cap"| VAL["Validation Agent<br/><i>6h re-propagation safety check</i>"]
 
    VAL -->|"8 · rejects_secondary_risk → loop back with constraint"| OA
    VAL -->|"8 · approved / approved_no_action"| ORCH
 
    ORCH -->|"WebSocket broadcast"| FE["React Frontend<br/>3D globe (react-globe.gl) + negotiation console"]
    ORCH -->|"9 · log session"| DB[("SQLite<br/>storage/db.py")]
 
    classDef det fill:#143120,stroke:#22c55e,color:#f2f4f8;
    classDef orch fill:#161c2a,stroke:#2e3750,color:#f2f4f8,stroke-width:2px;
    classDef neg fill:#1e3a5f,stroke:#3b82f6,color:#f2f4f8;
    classDef val fill:#3a2e0f,stroke:#f59e0b,color:#f2f4f8;
    classDef store fill:#10151f,stroke:#232a3b,color:#f2f4f8;
 
    class MON det;
    class ORCH orch;
    class OA,OB neg;
    class VAL val;
    class CT,FE,DB store;
```

**Backend:** FastAPI · WebSockets · `sgp4` · Pydantic · Anthropic API
**Frontend:** React + Vite · `react-globe.gl` · `satellite.js` · Tailwind CSS · Zustand
**Data:** CelesTrak (TLE, no auth) · NOAA SWPC (space weather — stretch goal, not implemented)

 Full technical detail in [`context/architecture.md`](context/architecture.md).

---

## What's Real vs. Simulated

We're upfront about this, since it matters for evaluating the demo honestly:

| Component | Status |
|---|:---:|
| Satellite tracking data | 🟢 **Real** — CelesTrak TLEs, real SGP4 propagation (independently verified against a known reference position) |
| Conjunction detection | 🟢 **Real** — actual computed miss-distance/TCA on a scripted scenario |
| Negotiation math (`yield_score`, Δv) | 🟢 **Real** — deterministic, auditable, traced to source in every UI display |
| Trajectory simulation | 🟢 **Real** — Keplerian two-body + J2 oblateness, RK4 integration |
| LLM negotiation narration | 🟢 **Real LLM calls**, with a deterministic template fallback if unavailable |


---

## Getting Started

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The backend runs entirely on cached/seeded data by default — no external API calls are required to see the full demo.

---

## Project Structure

See [`AGENTS.md`](AGENTS.md) and [`context/`](context/) for the full technical documentation this project was built against — architecture, design system, coding standards, and the phased build plan.

---

## Team

Built by:

| Name | Role | GitHub |
|---|---|---|
| Samarth Kulkarni | Orbital Physics & Conjunction Detection | [@SamarthKulkarni-2005](https://github.com/SamarthKulkarni-2005) |
| Samarth P Rao | Orchestrator, Schemas & Realtime Backbone | [@Atomiicradius](https://github.com/Atomiicradius) |
| Samarth Sainath Naik | Agent Intelligence — Cost, Narration & Validation | [@Sxmxrth05](https://github.com/Sxmxrth05) |
| Rahul P | Frontend Experience & WebSocket Client | [@rahul-ez](https://github.com/rahul-ez) |

## Demo Video

[Link to demo video]
