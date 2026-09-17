# Worldshepherd Zeek vector[record] JSON prototype fixture.
# This fixture is synthetic and intentionally independent of production traffic.

redef LogAscii::use_json = T;

module WSVectorRecord;

export {
    redef enum Log::ID += { LOG };

    type Answer: record {
        rdata: string;
        ttl: count;
        note: string &optional;
    };

    type Info: record {
        ts: time &log;
        case_id: string &log;
        answers: vector of Answer &log &optional;
    };
}

event zeek_init()
    {
    Log::create_stream(WSVectorRecord::LOG, [$columns=Info, $path="ws-vector-record"]);

    local answers: vector of Answer;
    answers += Answer($rdata="192.0.2.10", $ttl=300, $note="first \"quoted\" answer");
    answers += Answer($rdata="192.0.2.11", $ttl=301);
    Log::write(WSVectorRecord::LOG, Info($ts=network_time(), $case_id="multiple", $answers=answers));

    local empty_answers: vector of Answer;
    Log::write(WSVectorRecord::LOG, Info($ts=network_time(), $case_id="empty", $answers=empty_answers));

    Log::write(WSVectorRecord::LOG, Info($ts=network_time(), $case_id="absent"));
    }
