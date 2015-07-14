## fuzzmon
An application layer proxy which attaches to the backend server to detect faults. It's puprpose is to record and proxy fuzzing traffic from clients, whilst gathering interesting crash information from the target using ptrace.

It tries to solve the problem of some network fuzzers: **which input caused which crash?** Since fuzzmon sees both the traffic in flight and the state of the application, it knows which input triggered which crash. It is also fast, since it does not require any form of fuzzing client/server synchronization.

Once a crash happens, it records interesting information as JSON blobs, and either exits or restarts the target process. The information within the JSON blob makes it easy to match the corresponding coredump. It also makes it easy to perform initial analysis on the recorded JSON.
## Installation
#### From pypi
```
pip install fuzzmon
```
#### From github
```
git clone https://github.com/alexmgr/fuzzmon/
```
## Usage
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
* `stream: `packet causing the crash (as well as previous packets within the stream) in hex format
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
 » fuzzmon -q -n -l WARNING -f -e -s a_session_id -c 10 -d tcp:0.0.0.0:1234 -u tcp:127.0.0.1:6666 vuln-server 6666
WARNING:root:Received signal 11 from process: 14612. Gathering crash information
WARNING:root:Propagating signal 11 to child process: 14612
WARNING:root:Detached from process: 14612
WARNING:root:Stopped debugger. Exiting now
WARNING:root:Upstream server crashed!
WARNING:root:Upstream server appears to be dead: <socket._socketobject object at 0x2ac3600>

 » nc 127.0.0.1 1234                               
abcdefgh
1234567890
qwertyuiop
^C

 » nc 127.0.0.1 1234
i'm going to crash soon
it's coming
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

 » cat metadata/14612.json 
{
    "stream": [
        "69276d20676f696e6720746f20637261736820736f6f6e0a", 
        "6974277320636f6d696e670a", 
        "41414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141414141410a"
    ], 
    "backtrace": {
        "0x400ea1L": [
            "???", 
            []
        ]
    }, 
    "pid": 14612, 
    "registers": {
        "gs": "0x0000000000000000", 
        "gs_base": "0x0000000000000000", 
        "rip": "0x0000000000400ea1", 
        "rdx": "0x0000000000000000", 
        "fs": "0x0000000000000000", 
        "cs": "0x0000000000000033", 
        "rax": "0x00007fff4c1c5e70", 
        "rsi": "0x0000000000000000", 
        "rcx": "0x00000000000000fb", 
        "es": "0x0000000000000000", 
        "r14": "0x0000000000000000", 
        "r15": "0x0000000000000000", 
        "r12": "0x0000000000400a80", 
        "r13": "0x00007fff4c1c6200", 
        "r10": "0x0000000000000000", 
        "r11": "0x00007eff8b0999a8", 
        "orig_rax": "0xffffffffffffffff", 
        "fs_base": "0x00007eff8b5a4700", 
        "rsp": "0x00007fff4c1c6128", 
        "ds": "0x0000000000000000", 
        "rbx": "0x0000000000000000", 
        "ss": "0x000000000000002b", 
        "r8": "0x0000000000000074", 
        "r9": "0x0000000000c00000", 
        "rbp": "0x4141414141414141", 
        "eflags": "0x0000000000010206", 
        "rdi": "0x00007fff4c1c6064"
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
        "STACK": "0x00007fff4c1a7000-0x00007fff4c1c8000 => [stack] (rwxp)", 
        "STACK-40": "0x4141414141414141", 
        "STACK-32": "0x4141414141414141", 
        "STACK-24": "0x4141414141414141", 
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
                "0x0000000000b8a000", 
                "0x0000000000bab000"
            ], 
            "[heap]", 
            "rwxp"
        ], 
        [
            [
                "0x00007eff8b016000", 
                "0x00007eff8b198000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007eff8b198000", 
                "0x00007eff8b398000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "---p"
        ], 
        [
            [
                "0x00007eff8b398000", 
                "0x00007eff8b39c000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007eff8b39c000", 
                "0x00007eff8b39d000"
            ], 
            "/lib/x86_64-linux-gnu/libc-2.13.so", 
            "rwxp"
        ], 
        [
            [
                "0x00007eff8b39d000", 
                "0x00007eff8b3a2000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007eff8b3a2000", 
                "0x00007eff8b3c2000"
            ], 
            "/lib/x86_64-linux-gnu/ld-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007eff8b5a3000", 
                "0x00007eff8b5a6000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007eff8b5be000", 
                "0x00007eff8b5c1000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007eff8b5c1000", 
                "0x00007eff8b5c2000"
            ], 
            "/lib/x86_64-linux-gnu/ld-2.13.so", 
            "r-xp"
        ], 
        [
            [
                "0x00007eff8b5c2000", 
                "0x00007eff8b5c3000"
            ], 
            "/lib/x86_64-linux-gnu/ld-2.13.so", 
            "rwxp"
        ], 
        [
            [
                "0x00007eff8b5c3000", 
                "0x00007eff8b5c4000"
            ], 
            "", 
            "rwxp"
        ], 
        [
            [
                "0x00007fff4c1a7000", 
                "0x00007fff4c1c8000"
            ], 
            "[stack]", 
            "rwxp"
        ], 
        [
            [
                "0x00007fff4c1f9000", 
                "0x00007fff4c1fb000"
            ], 
            "[vvar]", 
            "r--p"
        ], 
        [
            [
                "0x00007fff4c1fb000", 
                "0x00007fff4c1fd000"
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
    "time": 1436833472.281639, 
    "history": [
        [
            "61626364656667680a", 
            "313233343536373839300a", 
            "71776572747975696f700a"
        ]
    ]
}%
```
By setting the proper sysctls, you can record the pid in the coredump name. You should have all the information needed to automatically triage your crashes!
