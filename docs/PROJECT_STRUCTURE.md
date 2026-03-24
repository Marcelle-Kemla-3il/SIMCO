# Current Project Structure (Professional Layout)

This document reflects the **actual** folder organization.

## Top-level

- services — all backend services grouped by responsibility
	- services/quiz_backend — FastAPI quiz backend
	- services/face_backend — face confidence service + model assets
	- services/confidence_backend — true-confidence neural service
	- services/notification_backend — email notification service
- quiz-frontend — React/Vite frontend
- scripts — all operational/startup scripts
- docs — project documentation
- artifacts — generated snapshots/outputs
- data — runtime/session data

## Scripts

- scripts/windows/start-backend.bat
- scripts/windows/start-face-class.bat
- scripts/windows/start-frontend.bat
- scripts/windows/start-simco-logic.bat
- scripts/windows/start-notification.bat
- scripts/windows/docker-setup.ps1
- scripts/unix/docker-setup.sh

Root wrappers are preserved for compatibility:

- start-backend.bat
- start-face-class.bat
- start-frontend.bat
- start-simco-logic.bat
- start-notification.bat
- docker-setup.ps1
- docker-setup.sh

## Documentation

- docs/SETUP.md
- docs/TRAINING_GUIDE.md
- docs/STRUCTURE.md (legacy)
- docs/PROJECT_STRUCTURE.md (source of truth)
- docs/archive/* (historical docs)

## Artifacts

- artifacts/docker/from_docker_response.bin
- artifacts/docker/from_docker_response.png

## Notes

- All backend services are now consolidated under `services/` with explicit names by use.
- Reorganization focused on operational cleanliness: scripts, docs, and generated files are centralized.
