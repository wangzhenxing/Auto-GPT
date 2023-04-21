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
import logging
import threading
from typing import Iterator

import grpc

import message_pb2
import message_pb2_grpc


class ChatMaker:

    def __init__(self, executor: ThreadPoolExecutor, channel: grpc.Channel
                 ) -> None:
        self._executor = executor
        self._channel = channel
        self._stub = message_pb2_grpc.AutogptStub(self._channel)
        self._session_id = None
        self._audio_session_link = None
        self._call_state = None
        self._peer_responded = threading.Event()
        self._call_finished = threading.Event()
        self._consumer_future = None

    def _response_watcher(
            self,
            response_iterator: Iterator[message_pb2.AutogptResponse]) -> None:
        try:
            for response in response_iterator:
                # NOTE: All fields in Proto3 are optional. This is the recommended way
                # to check if a field is present or not, or to exam which one-of field is
                # fulfilled by this message.
                if response.HasField("ai_res"):
                    logging.info("chat response, thoughts=%s reasoning=%s plan=%s criticism=%s next_action=%s system_res=%s", 
                                 response.ai_res.thoughts, response.ai_res.reasoning, response.ai_res.plan, response.ai_res.criticism, 
                                 response.ai_res.next_action, response.ai_res.system_res)
                else:
                    raise RuntimeError(
                        "Received StreamCallResponse without call_info and call_state"
                    )
        except Exception as e:
            self._peer_responded.set()
            raise

    def send(self) -> None:
        request = message_pb2.AutogptRequest()
        request.ai_info.name = 'test_gpt_name'
        request.ai_info.role = 'test_gpt_role'
        request.ai_info.goals.append('search auto gpt from google')
        request.ai_info.goals.append('summarize the auto gpt, and wirte them to auto-gpt-cn1.txt')
        request.ai_info.goals.append('terminate')
        response_iterator = self._stub.autogptService(iter((request,)))
        # Instead of consuming the response on current thread, spawn a consumption thread.
        self._consumer_future = self._executor.submit(self._response_watcher,
                                                      response_iterator)

    def wait_peer(self) -> bool:
        logging.info("Waiting for peer to connect ...")
        self._peer_responded.wait(timeout=None)
        if self._consumer_future.done():
            # If the future raises, forwards the exception here
            self._consumer_future.result()
        return True


def process_chat(executor: ThreadPoolExecutor, channel: grpc.Channel
                 ) -> None:
    call_maker = ChatMaker(executor, channel)
    call_maker.send()
    if call_maker.wait_peer():
        logging.info("chat finished!")
    else:
        logging.info("chat failed: peer didn't answer")


def run():
    executor = ThreadPoolExecutor()
    with grpc.insecure_channel("localhost:5051") as channel:
        future = executor.submit(process_chat, executor, channel
                                 )
        future.result()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run()
