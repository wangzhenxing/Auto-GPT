# Copyright 2020 The gRPC Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from concurrent.futures import ThreadPoolExecutor
import json
import threading
from typing import Iterable
from colorama import Fore, Style

from autogpt.config.ai_config import AIConfig
from autogpt.config import Config
from autogpt.logs import logger, print_assistant_thoughts
from autogpt.memory import get_memory
from autogpt.app import execute_command, get_command
from autogpt.chat import chat_with_ai, create_chat_message
from autogpt.json_fixes.master_json_fix_method import fix_json_using_multiple_techniques
from autogpt.json_validation.validate_json import validate_json
from autogpt.speech import say_text
from autogpt.spinner import Spinner
from autogpt.utils import clean_input

from google.protobuf.json_format import MessageToJson
import grpc
from autogpt.agent import message_pb2
from autogpt.agent import message_pb2_grpc

class GrpcServer:

    def serve(self, address: str, port: str) -> None:
        server = grpc.server(ThreadPoolExecutor())
        message_pb2_grpc.add_AutogptServicer_to_server(Message(), server)
        server.add_insecure_port(address + ":" + port)
        server.start()
        logger.typewriter_log(
            "Server serving at ", Fore.YELLOW, address + ":" + port
        )
        server.wait_for_termination()


class Message(message_pb2_grpc.AutogptServicer):

    def __init__(self):
        self._id_counter = 0
        self._lock = threading.RLock()

    def autogptService(
        self, request_iterator: Iterable[message_pb2.AutogptRequest],
        context: grpc.ServicerContext
    ) -> Iterable[message_pb2.AutogptResponse]:
        try:
            request = next(request_iterator)
            name = request.ai_info.name
            role = request.ai_info.role
            goals = []
            logger.typewriter_log(
                "Received a request:  ", Fore.YELLOW, "ai name = " + request.ai_info.name + ", ai role=" + request.ai_info.role  
            )
            i=1
            for goal in request.ai_info.goals:
                goals.append(goal)
                logger.typewriter_log(
                    "Received a request:  goal", Fore.YELLOW, f"{i}:{goal}"
                )
                i+=1
        except StopIteration:
            raise RuntimeError("Failed to receive call request")

        try:
            conf = AIConfig(name, role, goals)
            cfg = Config()
            triggering_prompt = (
            "Determine which next command to use, and respond using the"
            " format specified above:"
            )
            system_prompt = conf.construct_full_prompt()
            memory = get_memory(cfg, init=True)

            self.ai_name = role
            self.memory = memory
            self.full_message_history = [] 
            self.next_action_count = 0
            self.system_prompt = system_prompt
            self.triggering_prompt = triggering_prompt
            
            cfg = Config()
            loop_count = 0
            command_name = None
            arguments = None
            user_input = ""

            while True:
                # Discontinue if continuous limit is reached
                loop_count += 1
                if (
                    cfg.continuous_mode
                    and cfg.continuous_limit > 0
                    and loop_count > cfg.continuous_limit
                ):
                    logger.typewriter_log(
                        "Continuous Limit Reached: ", Fore.YELLOW, f"{cfg.continuous_limit}"
                    )
                    break

                # Send message to AI, get response
                with Spinner("Thinking... "):
                    assistant_reply = chat_with_ai(
                        self.system_prompt,
                        self.triggering_prompt,
                        self.full_message_history,
                        self.memory,
                        cfg.fast_token_limit,
                    )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument

                assistant_reply_json = fix_json_using_multiple_techniques(assistant_reply)

                # Print Assistant thoughts
                if assistant_reply_json != {}:
                    validate_json(assistant_reply_json, 'llm_response_format_1')
                    # Get command name and arguments
                    try:
                        print_assistant_thoughts(self.ai_name, assistant_reply_json)
                        command_name, arguments = get_command(assistant_reply_json)
                        # command_name, arguments = assistant_reply_json_valid["command"]["name"], assistant_reply_json_valid["command"]["args"]
                        if cfg.speak_mode:
                            say_text(f"I want to execute {command_name}")
                    except Exception as e:
                        logger.error("Error: \n", str(e))

                if not cfg.continuous_mode and self.next_action_count == 0:
                    ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
                    # Get key press: Prompt the user to press enter to continue or escape
                    # to exit
                    logger.typewriter_log(
                        "NEXT ACTION: ",
                        Fore.CYAN,
                        f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  "
                        f"ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
                    )
                    print(
                        "Enter 'y' to authorise command, 'y -N' to run N continuous "
                        "commands, 'n' to exit program, or enter feedback for "
                        f"{self.ai_name}...",
                        flush=True,
                    )
                    while True:
                        console_input = clean_input(
                            Fore.MAGENTA + "Input:" + Style.RESET_ALL
                        )
                        if console_input.lower().rstrip() == "y":
                            user_input = "GENERATE NEXT COMMAND JSON"
                            break
                        elif console_input.lower().startswith("y -"):
                            try:
                                self.next_action_count = abs(
                                    int(console_input.split(" ")[1])
                                )
                                user_input = "GENERATE NEXT COMMAND JSON"
                            except ValueError:
                                print(
                                    "Invalid input format. Please enter 'y -n' where n is"
                                    " the number of continuous tasks."
                                )
                                continue
                            break
                        elif console_input.lower() == "n":
                            user_input = "EXIT"
                            break
                        else:
                            user_input = console_input
                            command_name = "human_feedback"
                            break

                    if user_input == "GENERATE NEXT COMMAND JSON":
                        logger.typewriter_log(
                            "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
                            Fore.MAGENTA,
                            "",
                        )
                    elif user_input == "EXIT":
                        print("Exiting...", flush=True)
                        break
                else:
                    # Print command
                    logger.typewriter_log(
                        "NEXT ACTION: ",
                        Fore.CYAN,
                        f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}"
                        f"  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
                    )

                # Execute command
                if command_name is not None and command_name.lower().startswith("error"):
                    result = (
                        f"Command {command_name} threw the following error: {arguments}"
                    )
                elif command_name == "human_feedback":
                    result = f"Human feedback: {user_input}"
                else:
                    result = (
                        f"Command {command_name} returned: "
                        f"{execute_command(command_name, arguments)}"
                    )
                    if self.next_action_count > 0:
                        self.next_action_count -= 1

                memory_to_add = (
                    f"Assistant Reply: {assistant_reply} "
                    f"\nResult: {result} "
                    f"\nHuman Feedback: {user_input} "
                )

                self.memory.add(memory_to_add)

                next_action = f"COMMAND = {command_name}" + f"  ARGUMENTS = {arguments}"

                ## 返回结果给客户端
                yield self.create_response(assistant_reply_json, result, user_input, next_action)

                # Check if there's a result from the command append it to the message
                # history
                if result is not None:
                    self.full_message_history.append(create_chat_message("system", result))
                    logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
                else:
                    self.full_message_history.append(
                        create_chat_message("system", "Unable to execute command")
                    )
                    logger.typewriter_log(
                        "SYSTEM: ", Fore.YELLOW, "Unable to execute command"
                    )

        except Exception as e:
            logger.typewriter_log(
                "Failed to start agent: ", Fore.RED, e
            )
            return

    def create_response(self, assistant_reply_json, result, user_input, next_action) -> message_pb2.AutogptResponse:
        assistant_thoughts_reasoning = None
        assistant_thoughts_plan = None
        assistant_thoughts_speak = None
        assistant_thoughts_criticism = None
        if not isinstance(assistant_reply_json, dict):
            assistant_reply_json = {}
        assistant_thoughts = assistant_reply_json.get("thoughts", {})
        assistant_thoughts_text = assistant_thoughts.get("text")

        if assistant_thoughts:
            assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
            assistant_thoughts_plan = assistant_thoughts.get("plan")
            assistant_thoughts_criticism = assistant_thoughts.get("criticism")
            assistant_thoughts_speak = assistant_thoughts.get("speak")

        response = message_pb2.AutogptResponse()
        response.ai_res.thoughts = assistant_thoughts_text
        response.ai_res.reasoning = assistant_thoughts_reasoning
        response.ai_res.plan = assistant_thoughts_plan
        response.ai_res.criticism = assistant_thoughts_criticism
        response.ai_res.next_action = next_action
        response.ai_res.system_res = result
        return response

