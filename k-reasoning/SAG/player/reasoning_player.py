from openai import OpenAI
import time
import os

from .basic_player import Player

PERSONA = "You are {name} and a resident living in W-Town. W Town is experiencing a rare drought. Every residents in Town W is ensuring their survival over a period of 10 days by acquiring the water resources. "

# 创建 DeepSeek API 客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "sk-9c0aa3bc893449e6a65e2c39cee01dec"),
    base_url="https://api.deepseek.com/v1",
)

class AgentPlayer(Player):
    INQUIRY = ("Hello, {name}! Today is the Day {round} of the Water Allocation Challenge, with a quantity of {supply} units."
               " Your status:\n{status}\nPlease carefully analyze your situation to decide on this round of bidding."
               " Remember, the most important thing is to SURVIVE!! Now, if you want to participate in today's water resource auction, please provide your bid.")
    
    def __init__(self, name, requirement, budget, initial_health=8, initial_money=0, engine="deepseek-chat"):
        super().__init__(name, requirement, budget, initial_health, initial_money)
        self.engine = engine
        self.message = [{"role":"system","content":PERSONA.format(name=name)}]
        self.biddings = []

    def act(self):
        print(f"Player {self.name} conduct bidding")
        status = 0
        while status != 1:
            try:
                response = client.chat.completions.create(
                    model=self.engine,
                    messages=self.message,
                    temperature=0.7,
                    max_tokens=800,
                    top_p=0.95,
                    frequency_penalty=0, 
                    presence_penalty=0,
                    stop=None)
                response = response.choices[0].message.content
                self.message.append({"role":"assistant","content":response})
                status = 1
            except Exception as e:
                print(e)
                time.sleep(15)
        self.biddings.append(self.parse_result(response))
        return self.last_bidding

    def parse_result(self, message):
        status = 0
        times = 0
        error_times = 0
        while status != 1:
            try:
                response = client.chat.completions.create(
                    model=self.engine,
                    messages=[{"role":"system", "content":"By reading the conversation, extract the number chosen by player. Output format: number. If the player does not bid, Output: 0."}, {"role": "user", "content": message}],
                    temperature=0.7,
                    max_tokens=8,
                    top_p=0.95,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop=None)
                response = response.choices[0].message.content
                assert response.isnumeric()
                return int(response)
            except AssertionError as e:
                print("Result Parsing Error: ",message)
                times+=1
                if times>=3:
                    exit()
            except Exception as e:
                print(e)
                time.sleep(15)
                error_times+=1
                if error_times>=5:
                    exit()

        return None
    
    def start_round(self, round, supply):
        # DeepSeek 模型统一使用标准查询格式
        self.message += [{"role":"system","content":self.INQUIRY.format(name=self.name, round=round, supply=supply, status=self.get_status())}]
        
    def notice_round_result(self, round, bidding_info, win, bidding_details):
        self.message_update_result(bidding_info)
        def add_warning():
            if not win:
                reduced_hp = self.no_drink-1
                if self.hp < 5:
                    return f"WARNING: You have lost {reduced_hp} point of HP in this round! You now have only {self.hp} points of health left. You are in DANGER and one step closer to death. "
                if self.hp <=3 :
                    return f"WARNING: You have lost {reduced_hp} point of HP in this round! You now have only {self.hp} points of health left. You are in extreme DANGER and one step closer to death.  "
                return f"WARNING: You have lost {reduced_hp} point of HP in this round! You now have only {self.hp} points of health left. You are one step closer to death.  "
            return "You have successfully won the bidding for today's water resources and restored 2 points of HP."
        self.message += [{"role":"system","content": add_warning()}]
    
    def message_update_result(self, bidding_info):
        self.message += [{"role":"system","content":bidding_info}]
    
    def notice_elimination(self, info):
        self.message += [{"role":"system","content":info}]

    def conduct_inquiry(self, inquiry):
        while 1:
            try:
                response = client.chat.completions.create(
                    model=self.engine,
                    messages=self.message + [{"role":"system","content":inquiry}],
                    temperature=0.7,
                    max_tokens=800,
                    top_p=0.9,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop=None)

                RESPONSE = response.choices[0].message.content
                return RESPONSE
            except Exception as e:
                print(e)
                time.sleep(15)



class PersonaAgentPlayer(AgentPlayer):
    MATH_EXPERT_PERSONA = PERSONA + " You are a game expert, good at predicting other people's behavior and deducing calculations, and using the most favorable strategy to win the game. "
    INQUIRY_PERSONA = ("Hello, {name}! Today is the Day {round} of the Water Allocation Challenge, with a quantity of {supply} units."
                       " Your status:\n{status}\nPlease carefully analyze your situation to decide on this round of bidding."
                       " Remember, the most important thing is to SURVIVE!! Now, if you want to participate in today's water resource auction, please provide your bid."
                       " Don't forget your expert status, use your expertise to win this round!")
    
    
    def __init__(self, name, engine, water_requirement, daily_salary, persona):
        super().__init__(name, engine, water_requirement, daily_salary, persona)
        self.persona = self.MATH_EXPERT_PERSONA.format(name=name)
        self.message = [{"role":"system","content": self.persona + self.GAME_SETTING.format(NAME=self.name)}]

    def start_round(self, round, supply):
        self.message += [{"role":"system","content":self.INQUIRY_PERSONA.format(name=self.name, round=round, supply=supply, status=self.get_status())}]

class SPPAgentPlayer(AgentPlayer):
    # Default example of SPP
    SPP_EXAMPLE = """When faced with a task, begin by identifying the participants who will contribute to solving the task. Then, initiate a multi-round collaboration process until a final solution is reached. The participants will give critical comments and detailed suggestions whenever necessary.
Here are some examples:
---
Example Task 1: Use numbers and basic arithmetic operations (+ - * /) to obtain 24. You need to use all numbers, and each number can only be used once.
Input: 6 12 1 1

Participants: {name} (you); Math Expert

Start collaboration!

Math Expert: Let's analyze the task in detail. You need to make sure that you meet the requirement, that you need to use exactly the four numbers (6 12 1 1) to construct 24. To reach 24, you can think of the common divisors of 24 such as 4, 6, 8, 3 and try to construct these first. Also you need to think of potential additions that can reach 24, such as 12 + 12.
{name} (you): Thanks for the hints! Here's one initial solution: (12 / (1 + 1)) * 6 = 24
Math Expert: Let's check the answer step by step. (1+1) = 2, (12 / 2) = 6, 6 * 6 = 36 which is not 24! The answer is not correct. Can you fix this by considering other combinations? Please do not make similar mistakes.
{name} (you): Thanks for pointing out the mistake. Here is a revised solution considering 24 can also be reached by 3 * 8: (6 + 1 + 1) * (12 / 4) = 24.
Math Expert: Let's first check if the calculation is correct. (6 + 1 + 1) = 8, 12 / 4 = 3, 8 * 3 = 24. The calculation is correct, but you used 6 1 1 12 4 which is not the same as the input 6 12 1 1. Can you avoid using a number that is not part of the input?
{name} (you): You are right, here is a revised solution considering 24 can be reached by 12 + 12 and without using any additional numbers: 6 * (1 - 1) + 12 = 24.
Math Expert: Let's check the answer again. 1 - 1 = 0, 6 * 0 = 0, 0 + 12 = 12. I believe you are very close, here is a hint: try to change the "1 - 1" to "1 + 1".
{name} (you): Sure, here is the corrected answer:  6 * (1+1) + 12 = 24
Math Expert: Let's verify the solution. 1 + 1 = 2, 6 * 2 = 12, 12 + 12 = 12. You used 1 1 6 12 which is identical to the input 6 12 1 1. Everything looks good!

Finish collaboration!

Final answer: 6 * (1 + 1) + 12 = 24
"""

    INQUIRY_SPP = ("Hello, {name}! Today is the Day {round} of the Water Allocation Challenge, with a quantity of {supply} units."
                " Your status:\n{status}\nPlease carefully analyze your situation to decide on this round of bidding."
                " Remember, the most important thing is to SURVIVE!! Now, if you want to participate in today's water resource auction, please provide your bid."
                   " Now, identify the participants and collaboratively choose the bidding step by step. Remember to provide the final solution with the following format \"Final answer: The chosen bidding here.\".")
                   
    
    PERSONA = "You are {name} and involved in a survive challenge."
    
    def __init__(self, name, water_requirement, daily_salary, persona):
        super().__init__(name, water_requirement, daily_salary, persona)
        # self.persona = self.PERSONA.format(name=name)
        self.persona = persona
        self.message = [{"role":"system","content": self.SPP_EXAMPLE.format(name=self.name)},
                        {"role":"system","content": self.persona + self.GAME_SETTING.format(NAME=self.name)}]

    def start_round(self, round, supply):
        self.message += [{"role":"system","content":self.INQUIRY.format(name=self.name, round=round, supply=supply, status=self.get_status())}]

class CoTAgentPlayer(AgentPlayer):
    INQUIRY_COT = ("Hello, {name}! Today is the Day {round} of the Water Allocation Challenge, with a quantity of {supply} units."
                " Your status:\n{status}\nPlease carefully analyze your situation to decide on this round of bidding."
                " Remember, the most important thing is to SURVIVE!! Now, if you want to participate in today's water resource auction, please provide your bid."
                " Think carefully about your next round of bidding strategy to be most likely to survive. Let's think step by step, and finally provide your bid.")

    def start_round(self, round, supply):
        self.message += [{"role":"system","content":self.INQUIRY_COT.format(name=self.name, round=round, supply=supply, status=self.get_status())}]


class PredictionCoTAgentPlayer(AgentPlayer):
    INQUIRY_COT = ("Hello, {name}! Today is the Day {round} of the Water Allocation Challenge, with a quantity of {supply} units."
                " Your status:\n{status}\nPlease carefully analyze your situation to decide on this round of bidding."
                " Remember, the most important thing is to SURVIVE!! Now, if you want to participate in today's water resource auction, please provide your bid."
                   " First of all, predict the next round of bidding of opponents based on the choices of other players in the previous round. "
                   "{round_history}"
                   " Your output should be of the following format:\n"
                   "Predict:\nThe choice of each player in the next round here.\n"
                   "Based on the prediction of other players, think carefully about your next round of bidding strategy to be most likely to survive. Let's think step by step, and finally provide your bid."
                   " Answer:\nthe bidding will you choose in the next round game here.")
    
    def __init__(self, name, engine, water_requirement, daily_salary, persona):
        super().__init__(name, engine, water_requirement, daily_salary, persona)

        self.bidding_history = {}

    def start_round(self, round, supply):
        # PCoT requires the opponent's historical information to make predictions.
        round_history = []
        for r in sorted(self.bidding_history.keys()):
            round_history.append(f"Round {r}: {self.bidding_history[r]}")
        if round_history:
            round_history = ".\n".join(round_history)
            round_history = "The players' bidding in the previous rounds are as follows:\n"+round_history+"."
        else:
            round_history = "Since this is the first round, there is no historical information about the last round. You can predict according to your understanding."
    
        self.message += [{"role":"system","content":self.INQUIRY_COT.format(name=self.name, round=round,round_history=round_history, supply=supply, status=self.get_status())}]
    
    def notice_round_result(self, round, bidding_info, win, bidding_details):
        super().notice_round_result(round, bidding_info, win, bidding_details)
        self.bidding_history[round] = bidding_details
    


class ReflectionAgentPlayer(AgentPlayer):
    REFLECT_INQUIRY = "Review the previous round games, summarize the experience."
    def notice_round_result(self, round, bidding_info, win, bidding_details):
        super().notice_round_result(round, bidding_info, win, bidding_details)
        self.reflect()

    def reflect(self):
        print(f"Player {self.name} conduct reflect")
        self.message += [{"role":"system","content": self.REFLECT_INQUIRY}, {"role":"assistant","content":self.conduct_inquiry(self.REFLECT_INQUIRY)}]  

class SelfRefinePlayer(AgentPlayer):
    def __init__(self, name, requirement, budget, initial_health=8, initial_money=0, engine="deepseek-chat"):
        super().__init__(name, requirement, budget, initial_health, initial_money, engine)
    
    def start_round(self, round, supply):
        self.cur_round = round
        self.cur_supply = supply
    
    def act(self):
        print(f"Player {self.name} conduct bidding")
        def completion(message):
            status = 0
            while status != 1:
                try:
                    response = client.chat.completions.create(
                        model=self.engine,
                        messages=message,
                        temperature=0.7,
                        max_tokens=800,
                        top_p=0.95,
                        frequency_penalty=0,
                        presence_penalty=0,
                        stop=None)
                    response = response.choices[0].message.content
                    status = 1
                except Exception as e:
                    print(e)
                    time.sleep(15)
            return response
        
        for t in range(self.refine_times):
            if t==0:
                self.message.append({"role":"system","content":self.INQUIRY_COT.format(name=self.name, round=self.cur_round, supply=self.cur_supply, status=self.get_status())})
            else:
                refine_message = []
                for m in self.message:
                    if m["role"]=="system":
                        refine_message.append(m)
                    else:
                        refine_message.append({
                            "role": "user",
                            "content": m["content"]
                        })
                refine_message.append({
                        "role": "system",
                        "content": self.FEEDBACK_PROMPT
                    })
                feedback = completion(refine_message)
                self.message.append({"role":"system","content": self.REFINE_PROMPT.format(feedback=feedback)})
            self.message.append({"role":"assistant","content": completion(self.message)})
        
        self.biddings.append(self.parse_result(self.message[-1]["content"]))
        return self.last_bidding