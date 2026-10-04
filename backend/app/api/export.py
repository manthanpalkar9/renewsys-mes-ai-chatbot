import io, csv
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/export", tags=["Export"])

@router.post("/csv")
async def export_csv(data: dict, current_user: User = Depends(get_current_user)):
    columns = data.get("columns", [])
    rows = data.get("rows", [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"# Renewsys MES AI Chatbot Export"])
    writer.writerow([f"# Generated: {datetime.utcnow().isoformat()} UTC"])
    writer.writerow([f"# User: {current_user.username}"])
    writer.writerow([])
    writer.writerow(columns)
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode("utf-8")), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=export.csv"})
