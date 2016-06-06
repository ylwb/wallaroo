use "ponytest"
use "collections"
use "promises"
use "buffy/messages"
use "sendence/bytes"
use "debug"

actor Main is TestList
  new create(env: Env) =>
    PonyTest(env, this)

  new make(env: Env) => None

  fun tag tests(test: PonyTest) =>
//    test(_TestMetricsWireMsgNode)
//    test(_TestMetricsWireMsgBoundary)
//    test(_TestMonitoringHubEncoder)
    test(_DeserialiseByteArray)

class iso _DeserialiseByteArray is UnitTest
  fun name(): String => "buffy:DeserialiseByteArray"
  fun apply(h: TestHelper) ? =>
    let auth: AmbientAuth = h.env.root as AmbientAuth
    let node_name = "leader"
    let bms = recover trn BoundaryMetricsSummary(node_name) end

    bms.add_report(BoundaryMetricsReport(1, 0, 1465237852267, 1465237852270))
    let b' = MetricsMsgEncoder.boundarymetrics(consume bms, auth)

// captured from local encoder:
    let a': Array[U8 val] val = recover [
0, 0, 0, 143, 129, 0, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 0, 56, 0, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 136, 0, 0, 0, 0, 0, 0, 0, 128, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 88, 0, 0, 0, 0, 0, 0, 0, 96, 0, 0, 0, 0, 0, 0, 0, 126, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 107, 80, 251, 38, 85, 1, 0, 0, 110, 80, 251, 38, 85, 1, 0, 0, 108, 101, 97, 100, 101, 114, 0
] end

// captured from app before going over TCP:
    let a: Array[U8 val] val = recover [
0, 0, 0, 143, 115, 0, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 0, 56, 0, 0, 0, 0,
0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0,
0, 136, 0, 0, 0, 0, 0, 0, 0, 114, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
1, 0, 0, 0, 0, 0, 0, 0, 88, 0, 0, 0, 0, 0, 0, 0, 96, 0, 0, 0, 0, 0, 0, 0, 112,
0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 107, 80,
251, 38, 85, 1, 0, 0, 110, 80, 251, 38, 85, 1, 0, 0, 108, 101, 97, 100, 101,
114, 0
] end

// captured from bms pre tcp
    let a'': Array[U8 val] val = recover [
0, 0, 0, 143, 115, 0, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 0, 56, 0, 0, 0, 0,
0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0,
0, 136, 0, 0, 0, 0, 0, 0, 0, 114, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
1, 0, 0, 0, 0, 0, 0, 0, 88, 0, 0, 0, 0, 0, 0, 0, 96, 0, 0, 0, 0, 0, 0, 0, 112,
0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 85, 43, 29,
39, 85, 1, 0, 0, 93, 43, 29, 39, 85, 1, 0, 0, 108, 101, 97, 100, 101, 114, 0]
end

    let e' = recover val a''.slice(4) end
    let decoded = MetricsMsgDecoder(consume e', auth)

    match decoded
    | let n: NodeMetricsSummary val =>
      Debug("1")
    | let n: BoundaryMetricsSummary val =>
      Debug("2")
    else
      h.fail("Wrong decoded message type")
    end
    true

class iso _TestMetricsWireMsgNode is UnitTest
  fun name(): String => "buffy:MetricsWireMsgNode"

  fun apply(h: TestHelper) ? =>
    let auth: AmbientAuth = h.env.root as AmbientAuth
    let node_name = "NodeTest"
    let nms = recover trn NodeMetricsSummary(node_name) end
    nms.add_report(1, StepMetricsReport(1232143143, 1354551314))
    nms.add_report(1, StepMetricsReport(1232347892, 1354328734))
    nms.add_report(1, StepMetricsReport(1242596283, 1123612344))
    nms.add_report(1, StepMetricsReport(1298273467, 1354275829))
    nms.add_report(1, StepMetricsReport(1223498726, 1313488791))

    nms.add_report(2, StepMetricsReport(1232143112, 1354551313))
    nms.add_report(2, StepMetricsReport(1232347867, 1354328748))
    nms.add_report(2, StepMetricsReport(1242596287, 1123612390))
    nms.add_report(2, StepMetricsReport(1298273412, 1354275808))
    nms.add_report(2, StepMetricsReport(1223498723, 1313488789))

    let encoded = MetricsMsgEncoder.nodemetrics(consume nms, auth)
    // remove the bytes length segment from the array
    let e' = recover val encoded.slice(4) end
    let decoded = MetricsMsgDecoder(consume e', auth)
    match decoded
    | let n: NodeMetricsSummary val =>
      h.assert_eq[String](n.node_name, "NodeTest")
      h.assert_eq[U64](n.digests(2).reports(2).start_time, 1242596287)
      h.assert_eq[USize](n.size(), 10)
      h.assert_eq[U64](n.digests(1).reports(0).dt(),(1354551314-1232143143))
    else
      h.fail("Wrong decoded message type")
    end
    true

class iso _TestMetricsWireMsgBoundary is UnitTest
  fun name(): String => "buffy:MetricsWireMsgBoundary"

  fun apply(h: TestHelper) ? =>
    let auth: AmbientAuth = h.env.root as AmbientAuth
    let node_name = "BoundaryTest"
    let bms = recover trn BoundaryMetricsSummary(node_name) end

    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9143,
      91354551, 1232143112))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9147,
      91354328, 1354328748))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9196,
      91123612, 1313488789))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9173,
      91354275, 1313488789))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.ingress_egress(), 9198,
      91313488, 1354275829))

    let encoded = MetricsMsgEncoder.boundarymetrics(consume bms, auth)
    let e' = recover val encoded.slice(4) end
    let decoded = MetricsMsgDecoder(consume e', auth)

    match decoded
    | let n: BoundaryMetricsSummary val =>
      h.assert_eq[String](n.node_name, "BoundaryTest")
      h.assert_eq[U64](n.reports(1).start_time, 91354328)
      h.assert_eq[U64](n.reports(4).boundary_type,
        BoundaryTypes.ingress_egress())
      h.assert_eq[U64](n.reports(4).dt(), (1354275829-91313488))
    else
      h.fail("Wrong decoded message type")
    end

    true

class iso _TestMonitoringHubEncoder is UnitTest
  fun name(): String => "buffy:MonitoringHubEncoder"

  fun apply(h: TestHelper) ? =>
    h.long_test(1_000_000_000)
    let auth: AmbientAuth = h.env.root as AmbientAuth

    // Set up a NodeMetricsSummary and a BoundaryMetricsSummary
    let node_name = "Test"
    let nms:NodeMetricsSummary iso = recover NodeMetricsSummary(node_name) end
    nms.add_report(1, StepMetricsReport(1000, 1999))
    nms.add_report(1, StepMetricsReport(2000, 2999))
    nms.add_report(1, StepMetricsReport(3000, 3999))
    nms.add_report(1, StepMetricsReport(4000, 4999))
    nms.add_report(1, StepMetricsReport(5000, 5999))

    nms.add_report(2, StepMetricsReport(1000, 1999))
    nms.add_report(2, StepMetricsReport(2000, 2999))
    nms.add_report(2, StepMetricsReport(3000, 3999))
    nms.add_report(2, StepMetricsReport(4000, 4999))
    nms.add_report(2, StepMetricsReport(5000, 5999))

    let bms:BoundaryMetricsSummary iso =
      recover BoundaryMetricsSummary(node_name) end

    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9143,
      1000, 2999))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9147,
      1500, 3499))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9196,
      2500, 6000))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.source_sink(), 9173,
      2550, 5950))
    bms.add_report(BoundaryMetricsReport(BoundaryTypes.ingress_egress(), 9198,
      2000, 4000))

    // Set up metrics collector
    // use a test stream output
    let promise = Promise[String]
    promise.next[String](recover this~_fulfill(h) end)
    let output = MetricsAccumulatorActor(promise)
    let res = ResumableTest(output)
    let handler: MetricsCollectionOutputHandler iso =
      recover iso MetricsStringAccumulator(MonitoringHubEncoder, output) end

    let bin_selector: F64Selector val = recover val Log10Selector end
    let mc: MetricsCollection = MetricsCollection(bin_selector, 1,
                                                  consume handler)

    // Process summaries
    mc.process_summary(consume nms)
    mc.process_summary(consume bms)
    // Process the collection with the handlers array
    mc.send_output(res)

  fun tag _fulfill(h: TestHelper, value: String): String =>
    let arr = recover val value.array() end
    h.assert_eq[USize](value.size(), 5375)
    /* TODO: Parse the JSON and validate contents:
    for chunk in LengthParser(value.array()) do
      h.assert
    end
    */
    h.complete(true)
    value

  fun timed_out(h: TestHelper) =>
    h.complete(false)

class LengthParser is Iterator[String]
  let _data: Array[U8 val] val
  var _idx: USize = 0

  new create(data: Array[U8 val] val) =>
    _data= data

  fun ref has_next(): Bool =>
    _idx <= _data.size()

  fun ref next(): String val ? =>
    let s = _idx = _idx + 4
    let slc = _data.slice(s, _idx)
    var chunk = bytes_to_usize(slc)
    let s' = _idx = _idx + chunk
    let slc' = _data.slice(s', _idx).clone()
    String.create().append(slc').clone()

  fun tag bytes_to_usize(a: Array[U8 val] ref): USize ? =>
    ((a(0).u32() << 24) + (a(1).u32() << 16) + (a(2).u32() << 8) +
    a(3).u32()).usize()

actor ResumableTest is Resumable
  let _output: MetricsAccumulatorActor  tag
  new create(output: MetricsAccumulatorActor tag) =>
    _output = output

  be resume() =>
    _output.written()
