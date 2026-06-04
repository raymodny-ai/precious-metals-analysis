class Forum:
    def __init__(self):
        self.agents = {}
        self.history = []
    
    def register_agent(self, name, agent_instance):
        self.agents[name] = agent_instance
    
    def post_message(self, agent_name, message):
        timestamp = "now" # Placeholder
        entry = {'agent': agent_name, 'message': message, 'time': timestamp}
        self.history.append(entry)
        print(f"[{agent_name}]: {message}")
        return entry

    def get_history(self):
        return self.history
