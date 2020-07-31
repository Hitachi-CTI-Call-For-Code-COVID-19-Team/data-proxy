#!/usr/bin/env python3

# reference:
# https://cloud.ibm.com/docs/openwhisk?topic=openwhisk-pkg_ov

import argparse
import subprocess
import os
import sys
import util

COS_PACKAGE = 'cloud-object-storage'
CLOUDANT_PACKAGE = 'cloudant'
DOCS_PACKAGE = 'docs'
PUBLIC_API = 'public-api'
PRIVATE_API = 'private-api'


def parse_args(args):
  parser = argparse.ArgumentParser(description="""
  deploy api service functions onto IBM Cloud Functions.
  This requires an environment variable ${APIKEY} as your IAM API key.
  """)
  parser.add_argument('-o', '--operation', default='create', help='create|delete a dummy-generator')
  parser.add_argument('-r', '--region', default='jp-tok', help='region name')
  parser.add_argument('-g', '--resource-group', default='c4c-covid-19', help='resource Group Name')
  parser.add_argument('-n', '--namespace', default='data-proxy', help='namespace name for generator')
  parser.add_argument('-c', '--cos-keyname', default='',
    help='comma-separated keyname of cos credentials')
  parser.add_argument('-l', '--cloudant-keyname', default='',
    help='comma-separated keyname of cloudant credentials')
  parser.add_argument('-f', '--api-list-file', default='./.api-list', help='file path to store api list')

  return parser.parse_args(args)


def create(args):
  args = parse_args(args)

  util.login(args.region, args.resource_group)
  util.create_functions_namespace(args.namespace)

  # cloud object storage
  if util.check_functions_package_exists(COS_PACKAGE) is False:
    p1 = subprocess.Popen(
      ['sh', './install-cos-package.sh', args.region],
      stdout=subprocess.PIPE
    )
    print(p1.communicate()[0].decode('utf-8'))

  for key in args.cos_keyname.split(','):
    util.bind_functions_to_service_credentials(COS_PACKAGE, 'cloud-object-storage', key)

  # cloudant
  if util.check_functions_package_exists(CLOUDANT_PACKAGE) is False:
    util.bind_functions_predefined_to('/whisk.system/cloudant', CLOUDANT_PACKAGE)

  for key in args.cloudant_keyname.split(','):
    util.bind_functions_to_service_credentials(CLOUDANT_PACKAGE, 'cloudantnosqldb', key)

  # public api (read) for cloud object storage, which should be http that can handle http raw
  util.update_functions_action_to_web(COS_PACKAGE, 'object-read', 'raw')
  util.create_functions_api(
    PUBLIC_API, '/public/api', '/files', 'post', '{}/object-read'.format(COS_PACKAGE), 'http'
  )
  # public api (read) for cloudant
  util.create_functions_package(DOCS_PACKAGE)
  util.create_functions_sequence(
    '{}/query'.format(DOCS_PACKAGE), ['{}/exec-query-find'.format(CLOUDANT_PACKAGE)])
  util.update_functions_action_to_web(DOCS_PACKAGE, 'query', 'true')
  util.create_functions_api(
    PUBLIC_API, '/public/api', '/docs', 'post', '{}/query'.format(DOCS_PACKAGE), 'json'
  )

  # private api (write) for cloud object storage, which should be http that can handle http raw
  util.update_functions_action_to_web(COS_PACKAGE, 'object-write', 'raw')
  util.create_functions_api(
    PRIVATE_API, '/private/api', '/files', 'post', '{}/object-write'.format(COS_PACKAGE), 'http'
  )

  # tired to debug.... this is alternative way to create api
  # util.create_functions_action(
  #   DOCS_PACKAGE, 'object-http-write', '../components/object-write-http.js', 'nodejs:10', '60000'
  # )
  # util.update_functions_action_to_web(DOCS_PACKAGE, 'object-http-write', 'raw')
  # util.create_functions_sequence('{}/object-write'.format(DOCS_PACKAGE), [
  #   '{}/object-http-write'.format(DOCS_PACKAGE),
  #   '{}/object-write'.format(COS_PACKAGE)
  # ])
  # util.update_functions_action_to_web(DOCS_PACKAGE, 'object-write', 'raw')
  # util.create_functions_api(
  #   PRIVATE_API, '/private/api', '/files', 'post', '{}/object-write'.format(DOCS_PACKAGE), 'http'
  # )

  # private api (write) for cloudant
  util.create_functions_sequence(
    '{}/doc-write'.format(DOCS_PACKAGE), ['{}/create-document'.format(CLOUDANT_PACKAGE)])
  util.update_functions_action_to_web(DOCS_PACKAGE, 'doc-write', 'true')
  util.create_functions_api(
    PRIVATE_API, '/private/api', '/docs', 'post', '{}/doc-write'.format(DOCS_PACKAGE), 'json'
  )

  public_url = util.get_functions_api_url('public-api')
  private_url = util.get_functions_api_url('private-api')
  with open(args.api_list_file, 'w') as f:
    f.write('{}={}\n'.format('PUBLIC_API_FILES', '{}/files'.format(public_url)))
    f.write('{}={}\n'.format('PUBLIC_API_DOCS', '{}/docs'.format(public_url)))
    f.write('{}={}\n'.format('PRIVATE_API_FILES', '{}/files'.format(private_url)))
    f.write('{}={}\n'.format('PRIVATE_API_DOCS', '{}/docs'.format(private_url)))

  # we have no cli i/f to create api key associated with this api...
  # add index


def delete(args):
  args = parse_args(args)

  util.login(args.region, args.resource_group)

  for pkg in util.get_functions_action_list(args.namespace, COS_PACKAGE):
    util.delete_functions_action(COS_PACKAGE, pkg)
  util.delete_functions_package(COS_PACKAGE)

  for pkg in util.get_functions_action_list(args.namespace, CLOUDANT_PACKAGE):
    util.delete_functions_action(CLOUDANT_PACKAGE, pkg)
  util.delete_functions_package(CLOUDANT_PACKAGE)

  util.delete_functions_action(DOCS_PACKAGE, 'query')
  util.delete_functions_package(DOCS_PACKAGE)

  util.delete_functions_namespace(args.namespace)


if __name__ == '__main__':
  args = parse_args(sys.argv[1:])
  if args.operation == 'create':
    create(sys.argv[1:])
  elif args.operation == 'delete':
    delete(sys.argv[1:])
  else:
    print(util.bcolors.WARNING + 'no option. please check usage of this script.' + util.bcolors.ENDC)
