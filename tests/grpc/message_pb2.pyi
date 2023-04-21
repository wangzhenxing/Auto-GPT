from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AIInfo(_message.Message):
    __slots__ = ["goals", "name", "role"]
    GOALS_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    goals: _containers.RepeatedScalarFieldContainer[str]
    name: str
    role: str
    def __init__(self, name: _Optional[str] = ..., role: _Optional[str] = ..., goals: _Optional[_Iterable[str]] = ...) -> None: ...

class AIRes(_message.Message):
    __slots__ = ["criticism", "next_action", "plan", "reasoning", "system_res", "thoughts"]
    CRITICISM_FIELD_NUMBER: _ClassVar[int]
    NEXT_ACTION_FIELD_NUMBER: _ClassVar[int]
    PLAN_FIELD_NUMBER: _ClassVar[int]
    REASONING_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_RES_FIELD_NUMBER: _ClassVar[int]
    THOUGHTS_FIELD_NUMBER: _ClassVar[int]
    criticism: str
    next_action: str
    plan: str
    reasoning: str
    system_res: str
    thoughts: str
    def __init__(self, thoughts: _Optional[str] = ..., reasoning: _Optional[str] = ..., plan: _Optional[str] = ..., criticism: _Optional[str] = ..., next_action: _Optional[str] = ..., system_res: _Optional[str] = ...) -> None: ...

class AutogptRequest(_message.Message):
    __slots__ = ["ai_info"]
    AI_INFO_FIELD_NUMBER: _ClassVar[int]
    ai_info: AIInfo
    def __init__(self, ai_info: _Optional[_Union[AIInfo, _Mapping]] = ...) -> None: ...

class AutogptResponse(_message.Message):
    __slots__ = ["ai_res"]
    AI_RES_FIELD_NUMBER: _ClassVar[int]
    ai_res: AIRes
    def __init__(self, ai_res: _Optional[_Union[AIRes, _Mapping]] = ...) -> None: ...
