const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const collection = JSON.parse(fs.readFileSync(path.join(
  __dirname, 'Postman Collection/Collection/RAFS DDMS.postman_collection.json'
), 'utf8'));

function child(parent, name) {
  const item = parent.item.find(item => item.name === name);
  assert.ok(item, `Missing collection item: ${name}`);
  return item;
}

const cleanupScript = child(child(collection, 'Clean Up'), 'Clean up via storage')
  .event.find(event => event.listen === 'prerequest').script.exec.join('\n');
for (const status of [204, 404, 403, 500, null, undefined]) {
  test(`Storage cleanup encodes record IDs and checks response ${status}`, () => {
    const recordId = 'osdu:master-data--SampleAcquisitionJob:7%2F12-A-7%20D_Sample_249';
    const values = new Map([
      ['recordsToCleanUp', JSON.stringify([recordId])],
      ['varsToCleanUp', '[]'],
    ]);
    let sentUrl;
    const pm = {
      collectionVariables: {
        get: key => values.get(key),
        unset: key => values.delete(key),
      },
      environment: {
        get: key => ({STORAGE_HOST: 'example.invalid/api/storage/v2', 'data-partition-id': 'osdu', access_token: 'test-token'})[key],
      },
      variables: {replaceIn: value => value},
      setCollectionVar: (_pm, key, value) => values.set(key, value),
      test: (_name, callback) => callback(),
      expect: actual => ({
        to: {
          equal: expected => assert.equal(actual, expected),
          be: {oneOf: allowed => assert.ok(allowed.includes(actual))},
        },
      }),
      sendRequest: (request, callback) => {
        sentUrl = request.url;
        if (status === null || status === undefined) {
          callback(status === null ? new Error('network failure') : null);
          return;
        }
        callback(null, {
          code: status,
          text: () => 'test response',
        });
      },
    };
    const run = () => vm.runInNewContext(cleanupScript, {pm, console: {log() {}, error() {}}});
    if (status === 204 || status === 404) {
      run();
    } else {
      assert.throws(run, assert.AssertionError);
    }
    assert.equal(sentUrl, 'https://example.invalid/api/storage/v2/records/' + encodeURIComponent(recordId));
  });
}

const analyses = child(child(collection, 'v2'), 'Samples Analysis');
const relativePermeabilityV11 = child(child(analyses, 'Samples Analysis [Relative Permeability]'), 'v1.1.0');
const versionedDatasetVariable = 'relativepermeability_dataset_id_v1_1';

test('Relative Permeability 1.1.0 uploads its own versioned dataset before reading it', () => {
  const upload = child(relativePermeabilityV11, '06 - Add data');
  const read = child(relativePermeabilityV11, '07 - Get record data');
  assert.ok(relativePermeabilityV11.item.indexOf(upload) < relativePermeabilityV11.item.indexOf(read));
  assert.equal(upload.request.method, 'POST');
  assert.equal(upload.request.url.query.find(query => query.key === 'content_schema_version').value, '1.1.0');
  const payload = JSON.parse(upload.request.body.raw);
  assert.equal(payload.data.length, 1);
  assert.equal(payload.columns.length, payload.data[0].length);
  assert.equal(payload.data[0][payload.columns.indexOf('SamplesAnalysisID')], '{{relativepermeability_record_id}}:');
  const createRecord = child(child(child(analyses, 'Samples Analysis [Relative Permeability]'), 'common'), '01 - Create record');
  const wpcSampleIds = JSON.parse(createRecord.request.body.raw)[0].data.SampleIDs;
  assert.ok(wpcSampleIds.includes(payload.data[0][payload.columns.indexOf('SampleID')]), 'SampleID must belong to the WPC');
  const schema = JSON.parse(fs.readFileSync(path.join(
    __dirname, '../../../app/models/data_schemas/jsonschema/sample_analysis_api_v2/relative_permeability.1.1.0.json'
  ), 'utf8'));
  for (const requiredColumn of schema.required) {
    assert.ok(payload.columns.includes(requiredColumn), `Missing required column: ${requiredColumn}`);
  }
  assert.deepEqual(payload.data[0][payload.columns.indexOf('Meta')], []);
  assert.ok(upload.request.body.raw.includes(':reference-data--CoreAnalysisFluidType:'));
  assert.ok(!upload.request.body.raw.includes(':reference-data--SampleInjectionFluidType:'));
  assert.ok(read.request.url.raw.includes(`{{${versionedDatasetVariable}}}`));
  assert.ok(read.request.url.path.includes(`{{${versionedDatasetVariable}}}`));
  assert.equal(read.request.url.query.find(query => query.key === 'content_schema_version').value, '1.1.0');
});

for (const updatedWpc of [false, true]) {
  test(`Relative Permeability 1.1.0 captures and cleans up its dataset (updated WPC: ${updatedWpc})`, () => {
    const upload = child(relativePermeabilityV11, '06 - Add data');
    const datasetId = 'osdu:dataset--File.Generic:relativepermeability-run-owned:123';
    const body = updatedWpc
      ? {ddms_urn: `urn/test/${datasetId}`, updated_wpc_id: 'updated-record'}
      : {ddms_urn: `urn/test/${datasetId}/data`};
    const values = new Map();
    const cleanup = [];
    const pm = {
      response: {code: 200, json: () => body},
      test: (_name, callback) => callback(),
      expect: actual => ({
        to: {
          equal: expected => assert.equal(actual, expected),
          match: pattern => assert.match(actual, pattern),
        },
      }),
      setCollectionVar: (_pm, key, value) => values.set(key, value),
      addRecordToCleanUp: (_pm, id) => cleanup.push(id),
    };
    const script = upload.event.find(event => event.listen === 'test').script.exec.join('\n');
    vm.runInNewContext(script, {pm});
    assert.equal(values.get(versionedDatasetVariable), datasetId);
    assert.deepEqual(cleanup, ['osdu:dataset--File.Generic:relativepermeability-run-owned']);
  });
}

const blackOil = child(child(child(collection, 'v2'), 'Fluid Model'), 'Black Oil Fluid Model');
for (const responses of [[[], [], [{}]], Array(30).fill([])]) {
  test(`Black Oil 17a polls search data until rows appear (${responses.length} responses)`, () => {
    const request = child(blackOil, '17a - Search data filtered in by row');
    const script = request.event.find(event => event.listen === 'prerequest').script.exec.join('\n');
    const sent = [];
    const pm = {
      request: {url: {toString: () => request.request.url.raw}},
      variables: {replaceIn: value => value, get: () => '1.0.0'},
      environment: {get: () => 'value'},
      sendRequest: (options, callback) => {
        sent.push(options.url);
        const data = responses[sent.length - 1];
        callback(null, {code: 200, json: () => ({result: {data}})});
      },
    };
    vm.runInNewContext(script, {pm, setTimeout: callback => callback()});
    assert.equal(sent.length, responses.length);
    assert.ok(sent.every(url => url.includes('rows_filter=FluidModelID,eq,{{fluid_record_id}}:')));
  });
}

for (const [folder, prefix] of [
  ['Samples Analysis [Relative Permeability]', 'relativepermeability'],
  ['Samples Analysis [Wettability Index]', 'wettabilityindex'],
]) {
  const common = child(child(analyses, folder), 'common');
  for (const requestName of ['01 - Create record', '03 - Get versions']) {
    test(`${folder}: ${requestName} tolerates existing sandbox globals`, () => {
      const values = new Map();
      const cleanup = [];
      const recordId = 'osdu:work-product-component--SamplesAnalysis:run-owned';
      const pm = {
        response: {
          code: 200,
          json: () => ({recordIdVersions: [`${recordId}:123`], versions: [122, 123]}),
        },
        collectionVariables: {set: (key, value) => values.set(key, value)},
        addRecordToCleanUp: (_pm, id) => cleanup.push(id),
        test: (_name, callback) => callback(),
        expect: code => ({to: {be: {oneOf: allowed => assert.ok(allowed.includes(code))}}}),
      };
      const context = vm.createContext({pm});
      vm.runInContext('var data = "previous request";', context);
      const script = child(common, requestName).event.find(event => event.listen === 'test');
      vm.runInContext(script.script.exec.join('\n'), context);
      assert.equal(context.data, 'previous request');
      if (requestName === '01 - Create record') {
        assert.equal(values.get(`${prefix}_record_id`), recordId);
        assert.deepEqual(cleanup, [recordId]);
      } else {
        assert.equal(values.get(`${prefix}_record_version`), 123);
        assert.deepEqual(cleanup, []);
      }
    });
  }
}
