#!/usr/bin/env ruby
# Offline R6B2 YAML/static regression test. Uses Ruby's bundled Psych parser,
# then a deliberately small YAML 1.2/JSON-compatible scalar resolver. No YAML
# object loading, aliases, merge keys, duplicate keys or implicit on/off booleans.
require 'psych'
require 'json'

def strict_yaml(text)
  stream = Psych.parse_stream(text)
  raise 'one document required' unless stream.children.length == 1
  convert_yaml(stream.children.first.root)
end

def convert_yaml(node)
  raise 'missing node' unless node
  raise 'explicit tag forbidden' if node.respond_to?(:tag) && node.tag
  raise 'anchor forbidden' if node.respond_to?(:anchor) && node.anchor
  case node
  when Psych::Nodes::Mapping
    result = {}
    node.children.each_slice(2) do |key, value|
      raise 'scalar key required' unless key.is_a?(Psych::Nodes::Scalar)
      raise 'tagged/anchored key forbidden' if key.tag || key.anchor
      name = key.value
      raise 'merge key forbidden' if name == '<<'
      raise 'duplicate key: '+name if result.key?(name)
      result[name] = convert_yaml(value)
    end
    result
  when Psych::Nodes::Sequence
    node.children.map { |child| convert_yaml(child) }
  when Psych::Nodes::Scalar
    return node.value unless node.plain
    case node.value
    when '', '~', 'null', 'Null', 'NULL' then nil
    when 'true', 'True', 'TRUE' then true
    when 'false', 'False', 'FALSE' then false
    when /\A-?(?:0|[1-9][0-9]*)\z/ then Integer(node.value, 10)
    else node.value
    end
  else
    raise 'unsupported YAML node'
  end
end

def demand(value, reason)
  raise reason unless value
end

def validate_workflow(wf, kind)
  demand(wf.is_a?(Hash) && wf['on'].is_a?(Hash), 'on mapping required')
  expected = kind == 'gate' ? %w[workflow_dispatch push pull_request] : %w[push pull_request]
  demand(wf['on'].keys.sort == expected.sort, 'trigger set')
  demand(wf['permissions'] == {'contents'=>'read'}, 'workflow permissions')
  flat = JSON.generate(wf)
  demand(!flat.match?(/id-token|NETLIFY_AUTH_TOKEN|NETLIFY_TOKEN|PRIVATE_KEY/), 'credential capability')
  demand(wf['jobs'].is_a?(Hash) && !wf['jobs'].empty?, 'jobs required')
  wf['jobs'].each_value do |job|
    demand(!job.key?('permissions') || job['permissions'] == {'contents'=>'read'}, 'job permissions')
    demand(!job.key?('environment'), 'deployment environment')
    demand(job['steps'].is_a?(Array), 'steps required')
    job['steps'].each do |step|
      demand(step.is_a?(Hash), 'step mapping')
      demand(!step.key?('run') || step['run'].is_a?(String), 'run string')
      demand(!step.key?('uses') || step['uses'].match?(/\Aactions\/[a-z-]+@[a-f0-9]{40}\z/), 'immutable action')
    end
  end
  if kind == 'gate'
    demand(wf['name'] == 'Gate self-test', 'check identity')
    demand(wf['jobs'].keys == %w[offline corpus-build pilot-artifact preactivation llm], 'job identities')
    steps = wf['jobs']['offline']['steps']
    cli = steps.find { |x| x['run'].to_s.include?('reporting_workflow_cli_selftest.py') }
    demand(cli && cli['run'] == "python -I -B scripts/reporting_workflow_selftest.py\npython -I -B scripts/reporting_workflow_cli_selftest.py\n", 'mandatory CLI')
    demand(!cli.key?('if') && !cli.key?('continue-on-error'), 'CLI unconditional')
    demand(wf['jobs']['pilot-artifact']['env']['BTS_PRODUCTION_TRUST_SHA256'] == '${{ vars.BTS_PRODUCTION_TRUST_SHA256 }}', 'public pin')
    demand(wf['jobs']['llm']['if'] == "github.event_name == 'workflow_dispatch'", 'paid suite manual')
    demand(flat.scan(/secrets\./).length == 1 && wf['jobs']['llm']['env'] == {'ANTHROPIC_API_KEY'=>'${{ secrets.ANTHROPIC_API_KEY }}'}, 'only inherited manual model secret')
  else
    demand(wf['name'] == 'Publication verification' && wf['jobs'].keys == ['publication'], 'check identity')
    job = wf['jobs']['publication']
    demand(job['name'] == 'Trusted publication verification', 'stable required check')
    demand(job['defaults']['run'] == {'shell'=>'bash','working-directory'=>'trusted'}, 'trusted path')
    demand(job['env']['BTS_PRODUCTION_TRUST_SHA256'] == '${{ vars.BTS_PRODUCTION_TRUST_SHA256 }}', 'public pin')
    demand(job['env']['CANDIDATE_SHA'] == '${{ github.event.pull_request.head.sha || github.sha }}', 'candidate binding')
    demand(job['env']['TRUSTED_SHA'] == '${{ github.event.pull_request.base.sha || github.event.before }}', 'trusted binding')
    steps = job['steps']
    cli = steps.find { |x| x['run'].to_s.include?('reporting_workflow_cli_selftest.py') }
    demand(cli && cli['run'].include?('python -I -B scripts/reporting_workflow_cli_selftest.py') && !cli.key?('if') && !cli.key?('continue-on-error'), 'mandatory CLI')
    demand(steps.last['run'] == 'python -I scripts/reporting_workflow.py --candidate ../candidate --candidate-sha "$CANDIDATE_SHA" --trusted-sha "$TRUSTED_SHA" --approval-repository ../approval --approval-sha "$APPROVAL_SHA"', 'trusted verifier')
    demand(!flat.include?('secrets.'), 'no secrets')
  end
  true
end

if ARGV[0] == '--dump'
  puts JSON.pretty_generate(strict_yaml(File.read(ARGV.fetch(1))))
  exit
end

root = File.expand_path('..', __dir__)
rows = []
check = lambda do |name, &block|
  begin
    block.call
    rows << {name: name, ok: true}
  rescue StandardError => e
    rows << {name: name, ok: false, detail: e.message}
  end
end
reject = lambda do |&block|
  failed = false
  begin
    block.call
  rescue StandardError
    failed = true
  end
  raise 'negative accepted' unless failed
end
{'gate'=>'gate-selftest.yml', 'publication'=>'publication-verification.yml'}.each do |kind, file|
  text = File.read(File.join(root, '.github/workflows', file))
  wf = strict_yaml(text)
  check.call(kind+' strict YAML and static controls') { validate_workflow(wf, kind) }
  check.call(kind+' on remains a string key') { demand(wf.key?('on') && !wf.key?(true), 'on typed as bool') }
  job_id = kind == 'gate' ? 'pilot-artifact' : 'publication'
  mutations = {
    'pull_request_target'=>lambda { |x| x['on']['pull_request_target'] = nil },
    'write permission'=>lambda { |x| x['permissions']['contents'] = 'write' },
    'id-token'=>lambda { |x| x['permissions']['id-token'] = 'write' },
    'Netlify token'=>lambda { |x| x['jobs'][job_id]['env']['NETLIFY_AUTH_TOKEN'] = '${{ secrets.NETLIFY_AUTH_TOKEN }}' },
    'omit CLI regressions'=>lambda { |x| x['jobs'].each_value { |j| j['steps'].reject! { |s| s['run'].to_s.include?('reporting_workflow_cli_selftest.py') } } },
    'loosen public pin'=>lambda { |x| x['jobs'][job_id]['env']['BTS_PRODUCTION_TRUST_SHA256'] = '${{ vars.BTS_PRODUCTION_TRUST_SHA256 || "fallback" }}' },
    'job write'=>lambda { |x| x['jobs'][job_id]['permissions'] = {'contents'=>'write'} }
  }
  if kind == 'publication'
    mutations['trusted verifier path'] = lambda { |x| x['jobs'][job_id]['defaults']['run']['working-directory'] = 'candidate' }
    mutations['candidate SHA fallback'] = lambda { |x| x['jobs'][job_id]['env']['CANDIDATE_SHA'] = 'main' }
  end
  mutations.each do |name, change|
    check.call(kind+' rejects '+name) do
      bad = Marshal.load(Marshal.dump(wf)); change.call(bad)
      reject.call { validate_workflow(strict_yaml(JSON.generate(bad)), kind) }
    end
  end
end
{
  'unquoted colon-space'=>'run: python -m pip install --only-binary=:all: -r lock',
  'duplicate root'=>"on: {}\non: {}\n",
  'duplicate nested'=>"jobs:\n  a: {}\n  a: {}\n",
  'alias'=>"a: &a [1]\nb: *a\n",
  'merge key'=>"<<: {}\n",
  'tag'=>"a: !!str x\n",
  'multiple documents'=>"---\na: 1\n---\nb: 2\n"
}.each do |name, text|
  check.call('parser rejects '+name) { reject.call { strict_yaml(text) } }
end
puts JSON.pretty_generate({passed: rows.count { |r| r[:ok] }, total: rows.length, cases: rows})
exit(rows.all? { |r| r[:ok] } ? 0 : 1)
