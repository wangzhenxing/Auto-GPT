# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: message.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rmessage.proto\x12\x0cgrpc.autogpt\"3\n\x06\x41IInfo\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0c\n\x04role\x18\x02 \x01(\t\x12\r\n\x05goals\x18\x03 \x03(\t\"v\n\x05\x41IRes\x12\x10\n\x08thoughts\x18\x01 \x01(\t\x12\x11\n\treasoning\x18\x02 \x01(\t\x12\x0c\n\x04plan\x18\x03 \x01(\t\x12\x11\n\tcriticism\x18\x04 \x01(\t\x12\x13\n\x0bnext_action\x18\x05 \x01(\t\x12\x12\n\nsystem_res\x18\x06 \x01(\t\"7\n\x0e\x41utogptRequest\x12%\n\x07\x61i_info\x18\x01 \x01(\x0b\x32\x14.grpc.autogpt.AIInfo\"L\n\x0f\x41utogptResponse\x12%\n\x06\x61i_res\x18\x01 \x01(\x0b\x32\x13.grpc.autogpt.AIResH\x00\x42\x12\n\x10\x61utogpt_response2\\\n\x07\x41utogpt\x12Q\n\x0e\x61utogptService\x12\x1c.grpc.autogpt.AutogptRequest\x1a\x1d.grpc.autogpt.AutogptResponse(\x01\x30\x01\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'message_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _AIINFO._serialized_start=31
  _AIINFO._serialized_end=82
  _AIRES._serialized_start=84
  _AIRES._serialized_end=202
  _AUTOGPTREQUEST._serialized_start=204
  _AUTOGPTREQUEST._serialized_end=259
  _AUTOGPTRESPONSE._serialized_start=261
  _AUTOGPTRESPONSE._serialized_end=337
  _AUTOGPT._serialized_start=339
  _AUTOGPT._serialized_end=431
# @@protoc_insertion_point(module_scope)
