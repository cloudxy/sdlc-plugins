import csv
import io

def export_cases(rows, tenant_id):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "title", "status"])
    writer.writeheader()
    for row in rows:
        if row["status"] == "open":
            writer.writerow({key: row[key] for key in ("id", "title", "status")})
    return output.getvalue()
