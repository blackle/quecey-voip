#!/usr/bin/env bash

export QUECEY_VOIP_USERNAME="blackle"
export QUECEY_VOIP_PASSWORD="123456"
export QUECEY_VOIP_PORT="5061"
export QUECEY_VOIP_REGISTRAR_URI="sip:localhost"
export QUECEY_VOIP_ID_URI="sip:blackle@localhost"
exec $1
