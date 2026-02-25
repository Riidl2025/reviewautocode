import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

load_dotenv()

# -----------------------------
# AWS SETUP
# -----------------------------
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

startups_table = dynamodb.Table("startups")
results_table = dynamodb.Table("screening_results")


# -----------------------------
# PARSE createdAt SAFELY
# -----------------------------
def parse_created_at(value):
    try:
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)

        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


# -----------------------------
# FETCH LATEST SUBMITTED
# -----------------------------
def fetch_one_submitted_startup():
    try:
        response = startups_table.scan(
            FilterExpression=Attr("status").eq("submitted")
        )

        items = response.get("Items", [])

        if not items:
            return None

        items.sort(
            key=lambda x: parse_created_at(x.get("createdAt")),
            reverse=True
        )

        latest = items[0]

        print("Selected startup:", latest.get("id"))

        return latest

    except ClientError as e:
        print("Error fetching startups:", e)
        return None


# -----------------------------
# UPDATE STATUS
# -----------------------------
def update_startup_status(startup_id, status):
    try:
        startups_table.update_item(
            Key={"id": startup_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":val": status},
        )
    except ClientError as e:
        print("Error updating status:", e)


# -----------------------------
# STORE RESULT (FIXED)
# -----------------------------
def store_screening_result(startup, result):
    try:
        results_table.put_item(
            Item={
                "resultId": str(startup["id"]),
                "startupId": startup["id"],
                "startupName": startup.get("startupName", "Unknown"),
                "companyEmail": startup.get("companyEmail", ""),

                # ✅ CLEAN JSON (NO DynamoDB manual typing)
                "scoresJSON": {
                    "Founder_and_Team": result["Founder_and_Team"],
                    "Problem_and_Market": result["Problem_and_Market"],
                    "Solution_and_Product": result["Solution_and_Product"],
                    "Traction_and_Validation": result["Traction_and_Validation"],
                    "Business_Model_and_Scalability": result["Business_Model_and_Scalability"],
                    "Incubation_Fit": result["Incubation_Fit"],
                    "Total_Score": result["Total_Score"],
                    "Decision": result["Decision"],
                    "Reasoning": result["Reasoning"],
                    "Red_Flags": result.get("Red_Flags", []),
                },

                "totalScore": result["Total_Score"],
                "decision": result["Decision"],
                "reasoning": result["Reasoning"],
                "red_flags": result.get("Red_Flags", []),

                "emailSent": False,
                "createdAt": datetime.utcnow().isoformat(),
            }
        )

        print("✅ Stored result in DynamoDB")

    except ClientError as e:
        print("❌ Error storing result:", e)