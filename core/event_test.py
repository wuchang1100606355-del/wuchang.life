def run_event_test():
    event = {
        "type": "community_purchase",
        "amount": 1000,
        "mode": "simulation"
    }

    result = {
        "fund_total": event["amount"] * 0.3,
        "consumer_reward": event["amount"] * 0.135,
        "volunteer_pool": event["amount"] * 0.06,
        "social_welfare": event["amount"] * 0.015,
        "operation_cost": event["amount"] * 0.06,
        "rd_fund": event["amount"] * 0.03
    }

    print("Event:", event)
    print("Result:", result)
