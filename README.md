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
<img src="https://img.shields.io/badge/Anthropic%20Claude-D4A27F?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic Claude">
<br>
<img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
<img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
<img src="https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS">
<img src="https://img.shields.io/badge/Zustand-433E38?style=for-the-badge&logo=react&logoColor=white" alt="Zustand">
<br>
<img src="https://img.shields.io/badge/SGP4-orbital%20propagation-1e3a5f?style=for-the-badge" alt="SGP4">
<img src="https://img.shields.io/badge/react--globe.gl-3D%20globe-143120?style=for-the-badge" alt="react-globe.gl">
<img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
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
    A[("🛰️ CelesTrak<br/>real TLE data")] --> B

    subgraph DET["Deterministic — no LLM"]
        B["Conjunction Monitor Agent<br/><i>SGP4 propagation</i>"]
    end

    B -- "WebSocket · /ws/monitor" --> C

    subgraph NEG["Negotiation"]
        direction LR
        C["Operator Agent A"] <--> D["Operator Agent B"]
    end

    C -.->|"yield_score: deterministic<br/>justification: LLM narration"| C
    D -.->|"yield_score: deterministic<br/>justification: LLM narration"| D

    NEG -- "WebSocket · /ws/negotiation/{id}" --> E

    subgraph VAL["Validation — no LLM"]
        E["Validation Agent<br/><i>6h re-propagation safety check</i>"]
    end

    E --> F["React Frontend<br/>live 3D globe (react-globe.gl) + negotiation console"]
    E --> G[("SQLite<br/>session history")]

    classDef det fill:#143120,stroke:#22c55e,color:#f2f4f8;
    classDef neg fill:#1e3a5f,stroke:#3b82f6,color:#f2f4f8;
    classDef val fill:#3a2e0f,stroke:#f59e0b,color:#f2f4f8;
    classDef store fill:#10151f,stroke:#232a3b,color:#f2f4f8;

    class B det;
    class C,D neg;
    class E val;
    class A,F,G store;
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
| Mission priority / fuel data | 🟡 **Simulated** — no public API exposes real per-satellite operational data |
| LLM negotiation narration | 🟢 **Real LLM calls**, with a deterministic template fallback if unavailable |
| Session history persistence | 🟠 **Built, not yet live-wired** — `storage/db.py` has full save/query functions and passing tests, but the live negotiation flow doesn't call them yet; the History page falls back to bundled sample data until this lands |

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
