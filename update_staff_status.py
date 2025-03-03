import schedule
import time
from datetime import datetime
from supabase import create_client

# Your Supabase project URL and API key
SUPABASE_URL = "https://tmegfunkplvtdlmzgcvc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtZWdmdW5rcGx2dGRsbXpnY3ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk4NTcwMTUsImV4cCI6MjA1NTQzMzAxNX0.n5bYPpFujiJQoGF5ACI-TwfguLTsFROg8bK2XeqCLFY"
SUPABASE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtZWdmdW5rcGx2dGRsbXpnY3ZjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTg1NzAxNSwiZXhwIjoyMDU1NDMzMDE1fQ.GRq14NfLHUA3nOTwJY6ri5VsynS-HXOvx_zQQfgcEhM"

# Create a Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def update_staff_status():
    today = datetime.today().date()
    
    # Activate pending doctors and nurses whose start date has arrived
    supabase.table("doctor").update({"status": "active"}).eq("status", "pending").lte("startdate", today).execute()
    supabase.table("nurse").update({"status": "active"}).eq("status", "pending").lte("startdate", today).execute()

    # Expire active doctors and nurses whose contract has ended
    supabase.table("doctor").update({"status": "expired"}).eq("status", "active").lt("enddate", today).execute()
    supabase.table("nurse").update({"status": "expired"}).eq("status", "active").lt("enddate", today).execute()

    print(f"Staff status updated at {datetime.now()}")

# Schedule the job to run at midnight every day
schedule.every().day.at("00:00").do(update_staff_status)

print("Scheduled task running...")

while True:
    schedule.run_pending()
    time.sleep(60)  # Runs every minute to check for scheduled tasks
