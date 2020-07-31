import subprocess
import re
import os
import json
import uuid
from urllib import request

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'


'''
Fundamental Functions For IBM Cloud, like login and service creation
'''
def login(region, resource_group):
  print(bcolors.OKGREEN + 'Login to IBM Cloud' + bcolors.ENDC)

  subprocess.check_call(['ibmcloud', 'login', '--apikey', os.environ.get('APIKEY')])
  subprocess.check_call(['ibmcloud', 'target', '-r', region, '-g', resource_group])


def create_service_instance(instance_name, service, service_plan, region):
  print(bcolors.OKGREEN + 'Starting to create a instance {}'.format(instance_name) + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'resource', 'service-instances'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(['grep', instance_name], stdin=p1.stdout, stdout=subprocess.PIPE)
  p3 = subprocess.Popen(['wc', '-l'], stdin=p2.stdout, stdout=subprocess.PIPE)
  res = p3.communicate()[0]

  if int(res.decode('utf-8').strip()) == 0:
    # create an instance
    p1 = subprocess.Popen([
      'ibmcloud', 'resource', 'service-instance-create', instance_name, service,
      service_plan, region, '-p', '{"legacyCredentials": false}'
    ])
    p1.communicate()

    if p1.returncode != 0:
      print(bcolors.FAIL + 'failed to create instance {}'.format(instance_name) + bcolors.ENDC)
      raise Exception('failed to create instance {}'.format(instance_name))
  else:
    print(bcolors.OKGREEN + 'skip to create an instance {}'.format(instance_name) + bcolors.ENDC)

def get_tenant_id(instance_name):
  print(bcolors.OKGREEN + 'Starting to get a tenant id of {}'.format(instance_name) + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'resource', 'service-instance', instance_name], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(['awk', '-F:', '/^ID/ {print $9}'], stdin=p1.stdout, stdout=subprocess.PIPE)
  tenant_id = p2.communicate()[0].decode('utf-8').strip()

  if len(tenant_id) == 0:
    print(bcolors.FAIL + 'failed to get a tenant id of {}'.format(instance_name) + bcolors.ENDC)
    raise Exception('failed to get a tenant id of {}'.format(instance_name))

  print(bcolors.OKGREEN + 'got a tenant id {}'.format(tenant_id) + bcolors.ENDC)
  return tenant_id

def get_IAM_token():
  print(bcolors.OKGREEN + 'Starting to get an IAM token' + bcolors.ENDC)

  data = 'grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={}'.format(os.environ.get('APIKEY')).encode()
  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
  req = request.Request('https://iam.cloud.ibm.com/oidc/token', data = data, headers = headers)
  r = request.urlopen(req)
  token = 'Bearer ' + json.loads(r.read())['access_token']
  
  return token

def create_service_credential(keyname_prefix, role, instance_name, *args):
  print(
    bcolors.OKGREEN +
    'Starting to create {} service credential of {}'.format(role, instance_name) +
    bcolors.ENDC
  )

  # check if the key exists
  p1 = subprocess.Popen(['ibmcloud', 'resource', 'service-keys'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen([
    'awk', '/{}-{}/ {{print $2}}'.format(keyname_prefix, role.lower())
  ], stdin=p1.stdout, stdout=subprocess.PIPE)
  p3 = subprocess.Popen(['wc', '-l'], stdin=p2.stdout, stdout=subprocess.PIPE)
  res = p3.communicate()[0]

  if int(res.decode('utf-8').strip()) == 0:
    # create a credential
    p1 = subprocess.Popen([
      'ibmcloud', 'resource', 'service-key-create', '{}-{}'.format(keyname_prefix, role.lower()),
      role, '--instance-name', instance_name
    ] + list(args), stdout=subprocess.PIPE)
    wait = p1.communicate()
    if p1.returncode != 0:
      print(
        bcolors.FAIL +
        'cannot create {} service credentials for {}'.format(role, instance_name) +
        bcolors.ENDC
      )
      raise Exception('cannot create {} service credentials for {}'.format(role, instance_name))
    print(
      bcolors.OKGREEN + 'created a {} credential for {}'.format(role, instance_name) +
      bcolors.ENDC
    )

  # get credential as json
  p1 = subprocess.Popen([
    'ibmcloud', 'resource', 'service-key', '{}-{}'.format(keyname_prefix, role.lower()),
    '--output', 'json'
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode != 0:
      print(
        bcolors.FAIL +
        'cannot get {} service credentials for {}'.format(role, instance_name) +
        bcolors.ENDC
      )
      raise Exception('cannot get {} service credentials for {}'.format(role, instance_name))

  return json.loads(wait[0].decode('utf-8'))

def create_cloudant_credential(keyname_prefix, role, instance_name):
  cre = create_service_credential(keyname_prefix, role, instance_name)
  url = cre[0]['credentials']['url']

  m = re.match('https://(.*):(.*)@(.*)$', url)
  sc_username = m.group(1)
  sc_password = m.group(2)
  sc_url = 'https://{}'.format(m.group(3))

  return sc_username, sc_password, sc_url

def create_s3_hmac_credential(keyname_prefix, role, instance_name):
  cre = create_service_credential(keyname_prefix, role, instance_name, '--parameters', '{"HMAC":true}')

  return (
    cre[0]['credentials']['apikey'],
    cre[0]['credentials']['cos_hmac_keys']['access_key_id'],
    cre[0]['credentials']['cos_hmac_keys']['secret_access_key'],
    cre[0]['credentials']['endpoints']
  )

def delete_service_instance(instance_name, resource_group):
  print(
    bcolors.OKGREEN + 'Starting to delete an instance {}'.format(instance_name) +
    bcolors.ENDC
  )

  # check if it is
  p1 = subprocess.Popen(['ibmcloud', 'resource', 'service-instance', instance_name], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(['awk', '-F:', '/^ID/ {print $9}'], stdin=p1.stdout, stdout=subprocess.PIPE)
  wait = p2.communicate()
  if len(wait[0]) == 0:
    print(bcolors.FAIL + 'no instance {}, skip this operation'.format(instance_name) + bcolors.ENDC)
    return

  # delete an instance
  # delete all realated resources, like credentials tied to this instance
  p1 = subprocess.Popen([
    'ibmcloud', 'resource', 'service-instance-delete', instance_name,
    '-g', resource_group, '--force', '--recursive'
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()

  if p1.returncode != 0:
    print(bcolors.FAIL + 'failed to delete instance {}'.format(instance_name) + bcolors.ENDC)
    raise Exception('failed to delete instance {}'.format(instance_name))
  else:
    print(bcolors.OKGREEN + wait[0].decode('utf-8') + bcolors.ENDC)

'''
Functions for IBM Cloud Functions
'''
def create_functions_namespace(namespace):
  print(bcolors.OKGREEN + 'Starting to create a functions namespace' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'namespace', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(['grep', namespace], stdin=p1.stdout, stdout=subprocess.PIPE)
  wait = p2.communicate()
  if p2.returncode != 0:
    p1 = subprocess.Popen(['ibmcloud', 'fn', 'namespace', 'create', namespace], stdout=subprocess.PIPE)
    wait = p1.communicate()
    print(wait[0].decode('utf-8'))
    if p1.returncode != 0:
      print(bcolors.FAIL + 'cannot create namespace {}'.format(namespace) + bcolors.ENDC)
      raise Exception('cannot create namespace {}'.format(namespace))

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'property', 'set', '--namespace', namespace], stdout=subprocess.PIPE)
  print(p1.communicate()[0].decode('utf-8'))

def get_functions_namespace_id(namespace):
  print(bcolors.OKGREEN + 'Starting to get a functions namespace id' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'namespace', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(['awk', '/^{}/ {{print $3}}'.format(namespace)],
    stdin=p1.stdout, stdout=subprocess.PIPE)
  wait = p2.communicate()
  id = wait[0].decode('utf-8')
  if len(id) == 0:
    print(bcolors.FAIL + 'cannot get id of {}'.format(namespace) + bcolors.ENDC)
    raise Exception('cannot get id of {}'.format(namespace))

  return id

def check_functions_package_exists(package):
  print(bcolors.OKGREEN + 'Starting to check if {} exists'.format(package) + bcolors.ENDC)

  p1 = subprocess.Popen(
    ['ibmcloud', 'fn', 'package', 'list'], stdout=subprocess.PIPE
  )
  p2 = subprocess.Popen(['grep', package], stdin=p1.stdout, stdout=subprocess.PIPE)
  p2.communicate()

  if p2.returncode != 0:
    print(bcolors.OKGREEN + 'no {} package'.format(package) + bcolors.ENDC)
    return False

  print(bcolors.OKGREEN + '{} exists'.format(package) + bcolors.ENDC)
  return True

def create_functions_package(package):
  print(bcolors.OKGREEN + 'Starting to create a functions package' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'package', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(['grep', package], stdin=p1.stdout, stdout=subprocess.PIPE)
  wait = p2.communicate()
  if p2.returncode != 0:
    p1 = subprocess.Popen(['ibmcloud', 'fn', 'package', 'create', package], stdout=subprocess.PIPE)
    wait = p1.communicate()
    print(wait[0].decode('utf-8'))
    if p1.returncode != 0:
      print(bcolors.FAIL + 'cannot create package {}'.format(package) + bcolors.ENDC)
      raise Exception('cannot create package {}'.format(package))

def create_functions_action(package, action, file, kind, timeout):
  print(bcolors.OKGREEN + 'Starting to create a functions action' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'action', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen([
    'grep', '{}/{}'.format(package, action)
  ], stdin=p1.stdout, stdout=subprocess.PIPE)
  wait = p2.communicate()

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'action', 'create' if p1.returncode == 0 else 'update',
    '{}/{}'.format(package, action), file,
    '--kind', kind,
    '--timeout', timeout
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  print(wait[0].decode('utf-8'))
  if p1.returncode != 0:
    print(bcolors.FAIL + 'cannot create/update action {}/{}'.format(package, action) + bcolors.ENDC)
    raise Exception('cannot create/update action {}/{}'.format(package, action))

# if you want to add '--web-secure VALUE', use args
def update_functions_action_to_web(package, action, web_type, *args):
  print(bcolors.OKGREEN + 'Starting to update a functions action to web' + bcolors.ENDC)

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'action', 'update', '{}/{}'.format(package, action),
    '--web', web_type
  ] + list(args), stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode == 0:
    print(bcolors.OKBLUE + '{}'.format(wait[0].decode('utf-8')) + bcolors.ENDC)
  else:
    print(bcolors.FAIL + 'cannot update action {}/{} to web'.format(package, action) + bcolors.ENDC)
    raise Exception('cannot update action {}/{} to web'.format(package, action))

# you can add additional parameters for feed and trigger, like '--feed' 'something', ...
def create_functions_trigger(trigger, *args):
  print(bcolors.OKGREEN + 'Starting to create a trigger {}'.format(trigger) + bcolors.ENDC)

  p1 = subprocess.Popen(
    ['ibmcloud', 'fn', 'trigger', 'list'], stdout=subprocess.PIPE
  )
  p2 = subprocess.Popen(['grep', trigger], stdin=p1.stdout, stdout=subprocess.PIPE)
  p3 = subprocess.Popen(['wc', '-l'], stdin=p2.stdout, stdout=subprocess.PIPE)
  res = p3.communicate()[0]

  if int(res.decode('utf-8').strip()) == 0:
    # create
    p1 = subprocess.Popen(
      ['ibmcloud', 'fn', 'trigger', 'create', trigger] + list(args),
      stdout=subprocess.PIPE
    )
    wait = p1.communicate()
    if p1.returncode != 0:
      print(bcolors.FAIL + 'cannot create/update trigger {}'.format(trigger) + bcolors.ENDC)
      raise Exception('cannot create/update trigger {}'.format(trigger))
    else:
      print(wait[0].decode('utf-8'))
  else:
    print(
      bcolors.OKBLUE + 'the trigger {} already exists. skip to create it'.format(trigger) +
      bcolors.ENDC
    )

def create_functions_periodical_trigger(trigger, cron, trigger_params=None):
  trigger_payload = ()
  if trigger_params is not None:
    trigger_payload = ('--feed-param', 'trigger_payload', trigger_params)

  create_functions_trigger(
    trigger, '--feed', '/whisk.system/alarms/alarm', '--feed-param', 'cron', cron,
    *trigger_payload
  )

def create_functions_rule(rule, trigger, package, action):
  # ibmcloud fn rule create myRule everyOneMinute hello
  print(bcolors.OKGREEN + 'Starting to create a rule {}'.format(rule) + bcolors.ENDC)

  p1 = subprocess.Popen(
    ['ibmcloud', 'fn', 'rule', 'create', rule, trigger, '{}/{}'.format(package, action)],
    stdout=subprocess.PIPE
  )
  wait = p1.communicate()
  if p1.returncode != 0:
    print(bcolors.FAIL + 'cannot create/update a rule {}'.format(rule) + bcolors.ENDC)
    raise Exception('cannot create/update a rule {}'.format(rule))
  else:
    print(wait[0].decode('utf-8'))

def create_functions_sequence(sequence, actions, *args):
  print(bcolors.OKGREEN + 'Starting to create a sequece {}'.format(sequence) + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'action', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(
    ['grep', '{}'.format(sequence)], stdin=p1.stdout, stdout=subprocess.PIPE
  )
  p3 = subprocess.Popen(['wc', '-l'], stdin=p2.stdout, stdout=subprocess.PIPE)
  res = p3.communicate()[0]

  if int(res.decode('utf-8').strip()) == 0:
    p1 = subprocess.Popen([
      'ibmcloud', 'fn', 'action', 'create', sequence, '--sequence', ','.join(actions)
    ] + list(args), stdout=subprocess.PIPE)
    wait = p1.communicate()
    if p1.returncode != 0:
      print(bcolors.FAIL + 'cannot create/update sequence {}'.format(sequence) + bcolors.ENDC)
      raise Exception('cannot create/update sequence {}'.format(sequence))
    else:
      print(wait[0].decode('utf-8'))
  else:
    print(bcolors.OKBLUE + 'skip to create sequence {}'.format(sequence) + bcolors.ENDC)

# if you want to add '--config-file FILE', use *args
def create_functions_api(api_name, base_path, api_path, api_verb, action, response_type, *args):
  print(bcolors.OKGREEN + 'Starting to create an api {}'.format(api_name) + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'api', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(
    ['grep', '{}{}'.format(base_path, api_path)], stdin=p1.stdout, stdout=subprocess.PIPE
  )
  p3 = subprocess.Popen(['wc', '-l'], stdin=p2.stdout, stdout=subprocess.PIPE)
  res = p3.communicate()[0]

  if int(res.decode('utf-8').strip()) == 0:
    p1 = subprocess.Popen([
      'ibmcloud', 'fn', 'api', 'create', base_path, api_path, api_verb, action,
      '--apiname', api_name, '--response-type', response_type
    ] + list(args), stdout=subprocess.PIPE)
    wait = p1.communicate()
  
    if p1.returncode != 0:
      print(bcolors.FAIL + 'cannot create api {}'.format(api_name) + bcolors.ENDC)
      raise Exception('cannot create api {}'.format(api_name))
    else:
      print(wait[0].decode('utf-8'))
  else:
    print(bcolors.OKBLUE + 'Skip to craete an api {}'.format(api_name) + bcolors.ENDC)


# service is not insance name but service type, like cloud-object-storage
def bind_functions_to_service_credentials(target, service, key):
  print(
    bcolors.OKGREEN +
    'Starting to bind a package/action {} to a service {}'.format(target, service) +
    bcolors.ENDC
  )

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'service', 'bind', service, target, '--keyname', key
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode == 0:
    print(bcolors.OKGREEN + wait[0].decode('utf-8') + bcolors.ENDC)
  else:
    print(
      bcolors.FAIL +
      'cannot bind a package/action {} to a service {}'.format(target, service) +
      bcolors.ENDC
    )
    raise Exception('cannot bind a package/action {} to a service {}'.format(target, service))

def bind_functions_predefined_to(target, package):
  print(
    bcolors.OKGREEN +
    'Starting to bind a {} to a my env {}'.format(target, package) +
    bcolors.ENDC
  )

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'package', 'bind', target, package
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode == 0:
    print(bcolors.OKGREEN + wait[0].decode('utf-8') + bcolors.ENDC)
  else:
    print(
      bcolors.FAIL +
      'cannot bind a {} to my env {}'.format(target, package) +
      bcolors.ENDC
    )
    raise Exception('cannot bind a {} to my env {}'.format(target, package))

def get_functions_action_list(namespace, package):
  print(
    bcolors.OKGREEN +
    'Starting to get action list {}/{}'.format(namespace, package) +
    bcolors.ENDC
  )

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'property', 'set', '--namespace', namespace
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode == 0:
    # ibmcloud fn action list event-streams | awk '/event-streams/ {print $1}' | sed -e 's@.*/event-streams/\(.*\)@\1@g'
    p1 = subprocess.Popen(
      ['ibmcloud', 'fn', 'action', 'list', package], stdout=subprocess.PIPE
    )
    p2 = subprocess.Popen(
      ['awk', '/{}/ {{print $1}}'.format(package)], stdin=p1.stdout,
      stdout=subprocess.PIPE
    )
    # sed doesn't work
    wait = p2.communicate()
    return list(map(lambda x: re.sub('.*/{}/(.*)'.format(package), '\\1', x), list(filter(
      lambda x: len(x) > 0, wait[0].decode('utf-8').split('\n')
    ))))
  else:
    return []

def get_functions_package_or_action_parameters(isAction, target):
  print(
    bcolors.OKGREEN + 'Starting to get params of {}'.format(target) + bcolors.ENDC
  )

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', '{}'.format('action' if isAction is True else 'package'),
    'get', target, 'parameters'
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode == 0:
    print(bcolors.OKGREEN + wait[0].decode('utf-8') + bcolors.ENDC)
  else:
    print(
      bcolors.FAIL + 'cannot get params of {}'.format(target) + bcolors.ENDC
    )
    raise Exception('cannot get params of {}'.format(target))

def get_functions_api_url(api_name):
  print(
    bcolors.OKGREEN + 'Starting to get url of {}'.format(api_name) + bcolors.ENDC
  )

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'api', 'get', api_name, '-f'
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode == 0:
    return json.loads(wait[0].decode('utf-8'))['gwApiUrl']
  else:
    print(
        bcolors.FAIL + 'cannot get url of {}'.format(api_name) + bcolors.ENDC
    )
    raise Exception('cannot get url of {}'.format(api_name))

def delete_functions_action(package, action):
  print(bcolors.OKGREEN + 'Starting to delete a functions action' + bcolors.ENDC)

  p1 = subprocess.Popen([
    'ibmcloud', 'fn', 'action', 'delete', '{}/{}'.format(package, action)
  ], stdout=subprocess.PIPE)
  print(p1.communicate()[0].decode('utf-8'))

def delete_functions_package(package):
  print(bcolors.OKGREEN + 'Starting to delete a functions package' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'package', 'delete', package], stdout=subprocess.PIPE)
  print(p1.communicate()[0].decode('utf-8'))

def delete_functions_namespace(namespace):
  print(bcolors.OKGREEN + 'Starting to delete a functions namespace' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'namespace', 'delete', namespace], stdout=subprocess.PIPE)
  print(p1.communicate()[0].decode('utf-8'))

def delete_functions_trigger(trigger):
  print(bcolors.OKGREEN + 'Starting to delete a functions rule' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'trigger', 'delete', trigger], stdout=subprocess.PIPE)
  print(p1.communicate()[0].decode('utf-8'))

def delete_functions_rule(rule):
  print(bcolors.OKGREEN + 'Starting to delete a functions rule' + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'fn', 'rule', 'delete', rule], stdout=subprocess.PIPE)
  print(p1.communicate()[0].decode('utf-8'))


'''
Object Storage
'''
def create_buckets(buckets, region, tenant_id):
  print(bcolors.OKGREEN + 'Starting to create buckets' + bcolors.ENDC)

  for bucket in buckets:
    # check if the bucket is
    p1 = subprocess.Popen([
      'ibmcloud', 'cos', 'get-bucket-location', '--bucket', bucket
    ], stdout=subprocess.PIPE)
    p1.communicate()

    # create a bucket
    if p1.returncode != 0:
      p1 = subprocess.Popen([
        'ibmcloud', 'cos', 'create-bucket', '--bucket', bucket,
        '--ibm-service-instance-id', tenant_id, '--region', region
      ], stdout=subprocess.PIPE)
      print(p1.communicate()[0].decode('utf-8'))
      if p1.returncode != 0:
        print(bcolors.FAIL + 'cannot create bucket {}'.format(bucket) + bcolors.ENDC)
        raise Exception('cannot create bucket {}'.format(bucket))

def delete_buckets(buckets, region):
  print(bcolors.OKGREEN + 'Starting to delete buckets' + bcolors.ENDC)

  for bucket in buckets:
    # check if the bucket is
    p1 = subprocess.Popen([
      'ibmcloud', 'cos', 'get-bucket-location', '--bucket', bucket
    ], stdout=subprocess.PIPE)
    p1.communicate()

    # delete a bucket
    if p1.returncode == 0:
      p1 = subprocess.Popen([
        'ibmcloud', 'cos', 'delete-bucket', '--bucket', bucket, '--region', region, '--force'
      ], stdout=subprocess.PIPE)
      print(p1.communicate()[0].decode('utf-8'))
      if p1.returncode != 0:
        print(bcolors.FAIL + 'cannot delete bucket {}'.format(bucket) + bcolors.ENDC)
        raise Exception('cannot delete bucket {}'.format(bucket))

def put_objects(objects, region):
  for obj in objects:
    f, bucket = obj
    if os.path.exists(f) is True:
      p1 = subprocess.Popen([
        'ibmcloud', 'cos', 'put-object', '--bucket', bucket, '--key', os.path.basename(f),
        '--body', f, '--region', region
      ], stdout=subprocess.PIPE)
      wait = p1.communicate()
      
      if p1.returncode != 0:
        print(
          bcolors.FAIL + 'cannot upload data {} due to {}'.format(f, wait[0]) + bcolors.ENDC
        )
      else:
        print(wait[0].decode('utf-8'))
    else:
      print(bcolors.FAIL + 'there is no data {}'.format(f) + bcolors.ENDC)

def delete_objects(objects, region):
  obj = {}
  for o in objects:
    f, bucket = o
    if bucket in obj.keys():
      obj[bucket].append(os.path.basename(f))
    else:
      obj[bucket] = [os.path.basename(f)]
  
  for key in obj.keys():
    s = 'Objects=[' + ','.join([ '{{Key={}}}'.format(x) for x in obj[key] ]) + '],Quiet=false'
    p1 = subprocess.Popen([
        'ibmcloud', 'cos', 'delete-objects', '--bucket', key, '--delete', s,
        '--region', region
      ], stdout=subprocess.PIPE)
    wait = p1.communicate()

    if p1.returncode != 0:
      print(
        bcolors.FAIL + 'cannot delete keys {} due to {}'.format(obj[key], wait[0]) +
        bcolors.ENDC
      )
    else:
      print(wait[0].decode('utf-8'))


'''
Event Streams
'''
def event_streams_init(instance_name, admin_url):
  print(bcolors.OKGREEN + 'Starting to init {}'.format(instance_name) + bcolors.ENDC)

  p1 = subprocess.Popen([
    'ibmcloud', 'es', 'init', '--instance-name', instance_name, '--api-url', admin_url
  ], stdout=subprocess.PIPE)
  wait = p1.communicate()
  if p1.returncode != 0:
    print(bcolors.FAIL + 'failed to init {}'.format(instance_name) + bcolors.ENDC)
  else:
    print(wait[0].decode('utf-8'))

def create_topic(topics, partitions=1):
  print(bcolors.OKGREEN + 'Starting to create topics {}'.format(topics) + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'es', 'topics', '--json'], stdout=subprocess.PIPE)
  wait = p1.communicate()
  alltopics = json.loads(wait[0].decode('utf-8'))
  
  for topic in topics:
    if topic in alltopics:
      print(bcolors.OKBLUE + '{} exists. skip to create it'.format(topic) + bcolors.ENDC)
    else:
      p1 = subprocess.Popen([
        'ibmcloud', 'es', 'topic-create', '--name', topic,
        '--partitions', partitions
      ], stdout=subprocess.PIPE)
      # it doesn't return non-zero even when it fails.
      p2 = subprocess.Popen(['grep', 'OK'], stdin=p1.stdout, stdout=subprocess.PIPE)
      wait = p2.communicate()
      if (p2.returncode != 0):
        print(bcolors.FAIL + 'failed to create {}'.format(topic) + bcolors.ENDC)
      else:
        print(wait[0].decode('utf-8'))

def get_topic_detail(topic):
  print(bcolors.OKGREEN + 'Starting to getting topic detail {}'.format(topic) + bcolors.ENDC)

  p1 = subprocess.Popen(['ibmcloud', 'es', 'topic', topic, '--json'], stdout=subprocess.PIPE)
  wait = p1.communicate()
  # this command returns zero even if it fails.
  # but the message when failing is not json so that json.loads should raise when it fails.
  return json.loads(wait[0].decode('utf-8'))


'''
Utils
'''
def get_credentials_value(src, key):
  if os.path.exists(src) is True:
    with open(src) as f:
      line = f.readline()
      while line:
        kv = line.strip().split('=')
        if kv[0] == key:
          return kv[1]

        line = f.readline()

  return None

def copy_credentials_to_each(src, dst, map, addon):
  print(bcolors.OKGREEN + 'Copying credeitials to each json' + bcolors.ENDC)

  out = {}
  if os.path.exists(src) is True:
    with open(src) as f:
      line = f.readline()
      while line:
        kv = line.strip().split('=')
        for m in map:
          if kv[0] == m[0]:
            out[m[1]] = kv[1]

        line = f.readline()

    if addon is not None:
      for k, v in addon.items():
        out[k] = v

    if dst is not None:
      with open(dst, 'w') as f:
        json.dump(out, f)

  return out
