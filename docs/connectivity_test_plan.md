# Connectivity Test Plan

1. Start backend:
```bash
python run_api.py --host 0.0.0.0 --port 8001 --reload
```

2. Start frontend:
```bash
cd frontend
VITE_FRONTEND_API_BASE_URL=http://localhost:8001 npm run dev
```

3. Verify health:
```bash
curl http://localhost:8001/health
curl http://localhost:8001/api/v1/health
```

4. Upload files from UI.

5. Trigger pipeline run from UI.

6. Monitor status:
```bash
curl http://localhost:8001/api/v1/jobs/<job_id>/status
```

7. Fetch result:
```bash
curl http://localhost:8001/api/v1/jobs/<job_id>/result
```

8. Fetch dashboard:
```bash
curl "http://localhost:8001/api/v1/dashboard/Blue%20Star%20Ltd"
```

9. Download CAM:
```bash
curl -L "http://localhost:8001/api/v1/download/Blue%20Star%20Ltd/cam_pdf" -o CAM_report.pdf
```

10. Check backend logs:
```bash
tail -f logs/backend.log
```
