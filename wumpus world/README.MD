Wumpus World AI – Logic-Based Agent

Overview:
This project implements a Wumpus World AI agent using Propositional Logic and a Resolution-based Inference Engine.
Instead of simple rule-based movement, the agent uses logical reasoning to identify safe cells and navigate the environment.

The agent analyzes percepts such as Breeze, Stench, and Glitter to infer hazards and make safe decisions to reach the goal.

Features:
->Knowledge Base using Propositional Logic
->Resolution-based Inference Engine
->Percept handling (Breeze, Stench, Glitter)
->Safe cell detection using logical inference
->Web-based simulation using Flask

Tech Stack:
->Python
->Flask
->HTML, CSS, JavaScript

Logic: Resolution Algorithm

How It Works:
->The grid is generated with pits, a Wumpus, and gold
->The agent receives percepts from the environment
->These percepts are converted into logical clauses
->The inference engine derives safe cells
->The agent moves only to logically safe locations

Project Structure:
->kb.py: Knowledge Base and clause handling
->app.py: Flask backend and game logic
->templates/: Frontend UI

Purpose:
This project demonstrates a Knowledge-Based Agent using logical inference for decision-making in an uncertain environment.
