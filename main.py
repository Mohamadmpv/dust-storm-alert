import sys
import time
import asyncio
from datetime import datetime
from detector import detect_all
from notifier import send_alert, send_test_message, send_forecast_alert
from jalali import now_jalali


def run_once():
    print("=" * 60)
    print("Dust Storm Alert - " + now_jalali())
    print("=" * 60)
    print()
    print("Checking source points...")
    print()

    alerts, forecasts = detect_all()

    print()
    print("=" * 60)
    print("Current alerts:", len(alerts))
    print("Forecast alerts:", len(forecasts))
    print("=" * 60)

    if alerts:
        print("Sending current alerts to Bale...")
        send_alert(alerts)

    if forecasts:
        print("Sending forecast alerts to Bale...")
        send_forecast_alert(forecasts)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(send_test_message())
        print("Test message sent.")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        print("Starting loop mode - checks every hour.")
        while True:
            try:
                run_once()
            except Exception as e:
                print("Error:", e)
            print()
            print("Waiting 1 hour...")
            print()
            time.sleep(3600)
        return

    run_once()


if __name__ == "__main__":
    main()