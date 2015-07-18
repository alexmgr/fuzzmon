# fuzzmon

Ever wished you could just focus on data mutation and not fuzzing instrumentation? Fuzzmon let's you do just that. It takes care of the instrumentation and tracking of fuzzed inputs and let's you focus on building a good data model or fuzzing transform.

It's an application layer proxy which attaches to the backend server to detect faults. It's purpose is to record and proxy fuzzing traffic from clients, whilst gathering interesting crash information from the target using ptrace.

It tries to solve the problem of some network fuzzers: **which input caused which crash?** Since fuzzmon sees both the traffic in flight and the state of the application, it knows which input triggered which crash. It is also fast, since it does not require any form of fuzzing client/server synchronization.

Once a crash happens, it records interesting information as JSON blobs, and either exits or restarts the target process. The information within the JSON blob makes it easy to match the corresponding coredump. It also makes it easy to perform initial analysis on the recorded JSON.

`Fuzzmon` also provides `fuzzreplay`, which is able to replay a given JSON output against the server
## Installation
#### From pypi
```
pip install fuzzmon
```
#### From github
```
git clone https://github.com/alexmgr/fuzzmon/
```
## Fuzzmon usage
#### Get me started
Proxy all connections from tcp port `1234` to my target running on port `6666`. Also start the process (`vuln-server 6666`)
```python
 » ./fuzzmon -d tcp:0.0.0.0:1234 -u tcp:127.0.0.1:6666 vuln-server 6666
```
Proxy all connections from udp port `1234` to my target running unix socket `"/tmp/test"`. Also start the process (`vuln-server /tmp/test`). Follow fork() and execve()
```python
 » ./fuzzmon -f -e -d udp:0.0.0.0:1234 -u tcp:uds:/tmp/test vuln-server /tmp/test
```
Proxy all connections to tcp port `5555`, restart process automatically on crash, but wait for `45` seconds before doing so. Also set logging to `DEBUG`, redirect target stdout/stderr and accept `10` client connections:
```python
 » ./fuzzmon -w 45 -l DEBUG -n -c 10 -u tcp:127.0.0.1:5555 vuln-server 5555
```
You get the idea.
#### A bit more detail
Fuzzmon requires only 2 mandatory arguments:

1. The *binary and arguments* to run (or the *pid* (**-p**) to attach to)

2. The *upstream server* (**-u**) to connect to. Since fuzzmon uses ptrace to monitor the target, both fuzzmon and the target server must run on the same host. The following protocols are supported:
  * IPv4 (TCP or UDP)
  * IPv6 (TCP or UDP)
  * Unix Domain Sockets (UDS) (TCP or UDP)

#### Detailed usage

```
usage: fuzzmon [-h] [-p PID] -u UPSTREAM [-d DOWNSTREAM] [-o OUTPUT]
               [-s SESSION] [-f] [-e] [-n] [-c CONNS] [-q | -w WAIT]
               [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
               ...

A proxy which monitors the backend application state

positional arguments:
  program               The command line to run and attach to

optional arguments:
  -h, --help            show this help message and exit
  -p PID, --pid PID     Attach running process specified by its identifier
  -u UPSTREAM, --upstream UPSTREAM
                        Upstream server to which to connect. Format is
                        proto:host:port or uds:proto:file for Unix Domain
                        Sockets
  -d DOWNSTREAM, --downstream DOWNSTREAM
                        IP and port to bind to, or UDS. Format is
                        proto:host:port or uds:proto:file. By default, listen
                        to TCP connections on port 25746
  -o OUTPUT, --output OUTPUT
                        Output folder where to store the crash metadata
  -s SESSION, --session SESSION
                        A session identifier for the fuzzing session
  -f, --fork            Trace fork and child process
  -e, --trace-exec      Trace execve() event
  -n, --no-stdout       Use /dev/null as stdout/stderr, or close stdout and
                        stderr if /dev/null doesn't exist
  -c CONNS, --conns CONNS
                        Number of downstream connections to accept in
                        parallel. Default is 1
  -q, --quit            Do not restart the program after a fault is detected.
                        Exit cleanly
  -w WAIT, --wait WAIT  How long to wait for before restarting the crashed
                        process
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the debugging level
```
## Recording crashes
When a crash is detected, the following elements are extracted on compatible OS:
* `pip`: pid
* `stream`: packets causing the crash (as well as previous packets within the stream) in hex format. Each packet is tagged with the direction is has been seen in ("upstream" or "downstream")
* `stream_count`: stream count since beginning of fuzzing in hex format
* `history`: history of previous streams (up to 10)
* `backtrace`: backtrace
* `disassembly`: instruction causing the crash, as well as the 10 following instructions
* `maps`: memory mappings
* `stack`: state of the stack
* `time`: time of the crash
* `signal`: signal
* `session_id`: fuzzing session identifier

All output is written to a JSON blob which is identified by the process **pid**. Example output from a test run:
```python
 » fuzzmon -q -n -l WARNING -f -e -s a_session_id -d tcp:0.0.0.0:1234 -u tcp:127.0.0.1:6666 vuln-server 6666
 ....
 » nc 127.0.0.1 1234                               
abcdefgh
1234567890
qwertyuiop
^C
 » nc 127.0.0.1 1234
i'm going to crash soon
it's coming
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
 »
WARNING:DebuggingHooks:Received signal 11 from process: 13223. Gathering crash information
WARNING:DebuggingHooks:Propagating signal 11 to child process: 13223
WARNING:PtraceDbg:Detached from process: 13223
WARNING:PtraceDbg:Terminated process: 13223
WARNING:DebuggingHooks:Stopped debugger. Exiting now
WARNING:DebuggingHooks:Upstream server crashed!
WARNING:Downstream:Upstream server appears to be dead: <socket._socketobject object at 0x1bfb600>
WARNING:Downstream:Stopped downstream server

 » cat metadata/14612.json 
{
    "stream": [
        [
            "downstream", 
            "547970652051554954206f6e2061206c696e6520627920697473656c6620746f20717569740a"
        ], 
        [
            "upstream", 
            "69276d20676f696e6720746f20637261736820736f6f6e0a"
        ], 
        [
            "downstream", 
            "6e6f6f73206873617263206f7420676e696f67206d27690a"
        ], 
        [
            "upstream", 
            "6974277320636f6d696e670a"
        ], 
        [
            "downstream", 
            "676e696d6f6320732774690a"
        ], 
        [
            "upstream", 
            "41414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414242424242424242424242424242424242424242424242424242424242424242424242424242424242424242424242424343434343434343434343434343434343434343434343434343434343434343434343434343434344444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444440a"
        ]
    ], 
    "backtrace": {
        "0x400ea1L": [
            "???", 
            []
        ]
    }, 
    "pid": 13223, 
    "registers": {
        "gs": "0x0000000000000000", 
        "gs_base": "0x0000000000000000", 
        "rip": "0x0000000000400ea1", 
        "rdx": "0x0000000000000000", 
        "fs": "0x0000000000000000", 
        "cs": "0x0000000000000033", 
        "rax": "0x00007fffd7ab84c0", 
        "rsi": "0x0000000000000000", 
        "rcx": "0x00000000000000fb", 
        "es": "0x0000000000000000", 
        "r14": "0x0000000000000000", 
        "r15": "0x0000000000000000", 
        "r12": "0x0000000000400a80", 
        "r13": "0x00007fffd7ab8850", 
        "r10": "0x0000000000000000", 
        "r11": "0x00007f26a52e09a8", 
        "orig_rax": "0xffffffffffffffff", 
        "fs_base": "0x00007f26a57eb700", 
        "rsp": "0x00007fffd7ab8778", 
        "ds": "0x0000000000000000", 
        "rbx": "0x0000000000000000", 
        "ss": "0x000000000000002b", 
        "r8": "0x0000000000000074", 
        "r9": "0x0000000000c00000", 
        "rbp": "0x4141414141414141", 
        "eflags": "0x0000000000010206", 
        "rdi": "0x00007fffd7ab86b4"
    }, 
    "disassembly": {
        "0x400ea1L": "RET", 
        "0x400ea2L": "PUSH RBP", 
        "0x400ea3L": "MOV RBP, RSP", 
        "0x400ea6L": "SUB RSP, 0x140", 
        "0x400eadL": "MOV [RBP-0x134], EDI", 
        "0x400eb3L": "MOV [RBP-0xa0], RDX", 
        "0x400ebaL": "MOV [RBP-0x98], RCX", 
        "0x400ec1L": "MOV [RBP-0x90], R8", 
        "0x400ec8L": "MOV [RBP-0x88], R9", 
        "0x400ecfL": "TEST AL, AL"
    }, 
    "stack": {
        "STACK": "0x00007fffd7a99000-0x00007fffd7aba000 => [stack] (rwxp)", 
        "STACK-40": "0x4242424242424242", 
        "STACK-32": "0x4242424242424242", 
        "STACK-24": "0x4142424242424242", 
        "STACK-16": "0x4141414141414141", 
        "STACK -8": "0x4141414141414141", 
        "STACK +0": "0x4141414141414141", 
        "STACK +8": "0x4141414141414141", 
        "STACK+16": "0x4141414141414141", 
        "STACK+24": "0x4141414141414141", 
        "STACK+32": "0x4141414141414141", 
        "STACK+40": "0x4141414141414141"
    }, 
    "stream_count": 1, 
    "signal": "SIGSEGV", 
    "session_id": "a_session_id", 
    "maps": [
        [
            [
                "0x0000000000400000", 
                "0x0000000000402000"
            ], 
            "vuln-server", 
            "r-xp"
        ], 
        [
            [
                "0x0000000000601000", 
                "0x0000000000602000"
            ], 
            "vuln-server", 
            "rwxp"
        ], 
        [
            [
                "0x000000000162e000", 
                "0x000000000164f000"
            ], 
            "[heap]", 
            "rwxp"
        ], 
        [
            [
                "0x00007f26a525d000", 
                "0x00007f26a53df000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007f26a53df000", 
                "0x00007f26a55df000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "---p"
        ], 
        [
            [
                "0x00007f26a55df000", 
                "0x00007f26a55e3000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007f26a55e3000", 
                "0x00007f26a55e4000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "rwxp"
        ], 
        [
            [
                "0x00007f26a55e4000", 
                "0x00007f26a55e9000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007f26a55e9000", 
                "0x00007f26a5609000"
            ], 
            "/lib/x86_64-linux-gnu/ld-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007f26a57ea000", 
                "0x00007f26a57ed000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007f26a5805000", 
                "0x00007f26a5808000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007f26a5808000", 
                "0x00007f26a5809000"
            ], 
            "/lib/x86_64-linux-gnu/ld-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007f26a5809000", 
                "0x00007f26a580a000"
            ], 
            "/lib/x86_64-linux-gnu/ld-2.13.so", 
            "rwxp"
        ], 
        [
            [
                "0x00007f26a580a000", 
                "0x00007f26a580b000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007fffd7a99000", 
                "0x00007fffd7aba000"
            ], 
            "[stack]", 
            "rwxp"
        ], 
        [
            [
                "0x00007fffd7ad4000", 
                "0x00007fffd7ad6000"
            ], 
            "[vvar]", 
            "r--p"
        ], 
        [
            [
                "0x00007fffd7ad6000", 
                "0x00007fffd7ad8000"
            ], 
            "[vdso]", 
            "r-xp"
        ], 
        [
            [
                "0xffffffffff600000", 
                "0xffffffffff601000"
            ], 
            "[vsyscall]", 
            "r-xp"
        ]
    ], 
    "time": 1437179338.290207, 
    "history": [
        [
            [
                "downstream", 
                "547970652051554954206f6e2061206c696e6520627920697473656c6620746f20717569740a"
            ], 
            [
                "upstream", 
                "61626364656667680a"
            ], 
            [
                "downstream", 
                "68676665646362610a"
            ], 
            [
                "upstream", 
                "313233343536373839300a"
            ], 
            [
                "downstream", 
                "303938373635343332310a"
            ], 
            [
                "upstream", 
                "71776572747975696f700a"
            ], 
            [
                "downstream", 
                "706f69757974726577710a"
            ]
        ]
    ]
}
```
By setting the proper sysctls, you can record the pid in the coredump name. You should then have all the information needed to automatically triage your crashes!

## Fuzzreplay usage
`fuzzreplay` allows to replay crashes recorded by `fuzzmon`. Provide the target server address as well as the JSON dump, and `fuzzreplay` will reproduce the crash.
The last stream can be replayed or all streams (*-a*) in history can be replayed. That way it is possible to reproduce crashes which take a specific set of requests to trigger.
####Get me started
Just provide the target upstream server (*-u*) and the JSON to replay. Note that you can replay crashes directly to the server, or through `fuzzmon` if you wish to leverage application layer translation
```python
./fuzzreplay tests/integration/replay-test.json -a -u tcp:10.212.223.52:1234
WARNING:root:Sleeping for 3 seconds before sending alive test
WARNING:root:Performing alive test against target
Replay of stream 0 did not crash the server
WARNING:root:Sleeping for 3 seconds before sending alive test
WARNING:root:Performing alive test against target
WARNING:root:Stream replay failed: [Errno 61] Connection refused
Successfully crashed server by replaying stream 1:
[[u'downstream', u'547970652051554954206f6e2061206c696e6520627920697473656c6620746f20717569740a'], [u'upstream', u'3131313131313131313131313131313131323332343334330a'], [u'downstream', u'3334333432333231313131313131313131313131313131310a'], [u'upstream', u'333235313435333235323335323532333534323532330a'], [u'downstream', u'333235323435333235323533323532333534313532330a'], [u'upstream', u'414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141424242424242424242424242424242424242424242424242424242424242424242424242424242424242424242424242424343434343434343434343434343434343434343434343434343434343434343434343434343434343434343434444444444444444444444444444444444444444444444444444444444444444444444444444444444444545454545454545454545454545454545454545454545454545454545454545454545454545450a']]
```
#### Detailed usage
```python
usage: fuzzreplay [-h] -u UPSTREAM [-a] [-w WAIT]
                  [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                  filename

Replay streams captured by fuzzmon

positional arguments:
  filename              JSON test case to replay

optional arguments:
  -h, --help            show this help message and exit
  -u UPSTREAM, --upstream UPSTREAM
                        Upstream server to which to connect. Format is
                        proto:host:port or uds:proto:file for Unix Domain
                        Sockets
  -a, --all             Also replay all packets from history
  -w WAIT, --wait WAIT  Time to wait before performing alive test. Default is
                        3 seconds
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the debugging level

```
