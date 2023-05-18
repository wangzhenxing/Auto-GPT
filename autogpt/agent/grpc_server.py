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
from autogpt.commands.command import CommandRegistry
from colorama import Fore, Style

from autogpt.config.ai_config import AIConfig
from autogpt.config import Config
from autogpt.logs import logger, print_assistant_thoughts
from autogpt.memory import get_memory
from autogpt.app import execute_command, get_command
from autogpt.chat import chat_with_ai, create_chat_message
from autogpt.json_utils.json_fix_llm import fix_json_using_multiple_techniques
from autogpt.json_utils.utilities import validate_json
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
            self.triggering_prompt = triggering_prompt
            command_registry = CommandRegistry()
            command_registry.import_commands("autogpt.commands.analyze_code")
            command_registry.import_commands("autogpt.commands.audio_text")
            command_registry.import_commands("autogpt.commands.execute_code")
            command_registry.import_commands("autogpt.commands.file_operations")
            command_registry.import_commands("autogpt.commands.git_operations")
            command_registry.import_commands("autogpt.commands.google_search")
            command_registry.import_commands("autogpt.commands.image_gen")
            command_registry.import_commands("autogpt.commands.improve_code")
            command_registry.import_commands("autogpt.commands.twitter")
            command_registry.import_commands("autogpt.commands.web_selenium")
            command_registry.import_commands("autogpt.commands.write_tests")
            command_registry.import_commands("autogpt.app")
            self.command_registry = command_registry
            conf.command_registry = command_registry
            system_prompt = conf.construct_full_prompt()
            self.system_prompt = system_prompt
            self.config = conf
            
            loop_count = 0
            command_name = None
            arguments = None
            user_input = ""

            ## 返回结果给客户端
            j = 1
            for goal in goals:
                yield self.create_response('', '目标' + str(j) + '：' + goal, user_input, '')
                j += 1
            yield self.create_response('', '', user_input, 'Thinking...')

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

                logger.typewriter_log(
                    "test"
                )


                # Send message to AI, get response
                with Spinner("Thinking... "):
                    assistant_reply = chat_with_ai(
                        self,
                        self.system_prompt,
                        self.triggering_prompt,
                        self.full_message_history,
                        self.memory,
                        cfg.fast_token_limit,
                    ) 
                # TODO: This hardcodes the model to use GPT3.5. Make this an argument


                assistant_reply_json = fix_json_using_multiple_techniques(assistant_reply)
                for plugin in cfg.plugins:
                    if not plugin.can_handle_post_planning():
                        continue
                    assistant_reply_json = plugin.post_planning(self, assistant_reply_json)

                logger.typewriter_log('test1')
                # Print Assistant thoughts
                if assistant_reply_json != {}:
                    validate_json(assistant_reply_json, "llm_response_format_1")
                    # Get command name and arguments
                    try:
                        print_assistant_thoughts(self.ai_name, assistant_reply_json)
                        command_name, arguments = get_command(assistant_reply_json)
                        if cfg.speak_mode:
                            say_text(f"I want to execute {command_name}")
                    except Exception as e:
                        logger.error("Error: \n", str(e))

                ## 返回结果给客户端
                if command_name != "analyze_code":
                    yield self.create_response(assistant_reply_json, '', user_input, '')

                if not cfg.continuous_mode and self.next_action_count == 0:
                # ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
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
                        if console_input.lower().strip() == "y":
                            user_input = "GENERATE NEXT COMMAND JSON"
                            break
                        elif console_input.lower().strip() == "":
                            print("Invalid input format.")
                            continue
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

                #if command_name == 'write_to_file' or command_name == 'append_to_file':
                #    logger.typewriter_log(
                #        command_name,
                #        arguments,
                #    )
                    #arguments_dict = json.loads(arguments)
                    #text = arguments_dict['text']
                #    yield self.create_response('', arguments, user_input, '')

                logger.typewriter_log('test3')
                # Execute command
                if command_name is not None and command_name.lower().startswith("error"):
                    result = (
                        f"Command {command_name} threw the following error: {arguments}"
                    )
                elif command_name == "human_feedback":
                    result = f"Human feedback: {user_input}"
                else:
                    for plugin in cfg.plugins:
                        if not plugin.can_handle_pre_command():
                            continue
                        command_name, arguments = plugin.pre_command(
                            command_name, arguments
                        )
                    command_result = execute_command(
                        self.command_registry,
                        command_name,
                        arguments,
                        self.config.prompt_generator,
                    )
                    result = f"Command {command_name} returned: " f"{command_result}"

                    logger.typewriter_log(result)

                    for plugin in cfg.plugins:
                        if not plugin.can_handle_post_command():
                            continue
                        result = plugin.post_command(command_name, result)
                    if self.next_action_count > 0:
                        self.next_action_count -= 1
                if command_name != "do_nothing":
                    memory_to_add = (
                        f"Assistant Reply: {assistant_reply} "
                        f"\nResult: {result} "
                        f"\nHuman Feedback: {user_input} "
                    )

                    self.memory.add(memory_to_add)
                    ## 返回结果给客户端
                    if command_name != "analyze_code" \
                        and "No such file or directory" not in result:
                        yield self.create_response('', result, user_input, '')
                        ## 返回结果给客户端
                        yield self.create_response('', '', user_input, 'Thinking...')

                    # Check if there's a result from the command append it to the message
                    # history
                    if result is not None:
                        self.full_message_history.append(
                            create_chat_message("system", result)
                        )
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
        assistant_thoughts_reasoning = ''
        assistant_thoughts_plan = ''
        assistant_thoughts_speak = ''
        assistant_thoughts_criticism = ''
        if not isinstance(assistant_reply_json, dict):
            assistant_reply_json = {}
        assistant_thoughts = assistant_reply_json.get("thoughts", {})
        assistant_thoughts_text = assistant_thoughts.get("text", '')

        if assistant_thoughts:
            assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
            assistant_thoughts_plan = assistant_thoughts.get("plan")
            assistant_thoughts_criticism = assistant_thoughts.get("criticism")
            assistant_thoughts_speak = assistant_thoughts.get("speak")

        response = message_pb2.AutogptResponse()
        response.ai_res.thoughts = assistant_thoughts_text
        response.ai_res.reasoning = ""
        response.ai_res.plan = ""
        response.ai_res.criticism = ""
        response.ai_res.next_action = next_action
        response.ai_res.system_res = result
        return response

