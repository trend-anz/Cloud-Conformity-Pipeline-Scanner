"""
To use the script, specify the following required environment variables:
  * CC_API_KEY
  * CC_REGION
  * CFN_TEMPLATE_FILE_LOCATION

And, if necessary, the optional environment variable:
  * CC_RISK_LEVEL (default: LOW)
"""

import requests
import json
import os
import sys

CC_REGIONS = [
    'eu-west-1',
    'ap-southeast-2',
    'us-west-2',
]

RISK_LEVEL_NUMS = {
    'LOW': 0,
    'MEDIUM': 1,
    'HIGH': 2,
    'VERY_HIGH': 3,
    'EXTREME': 4,
}


class CcValidator:
    def __init__(self):

        try:
            print('Obtaining required environment variables...')
            self.cc_region = os.getenv('CC_REGION', 'us-west-2').lower()

            if self.cc_region not in CC_REGIONS:
                sys.exit('Error: Please ensure "CC_REGIONS" is set to a region which is supported by Cloud Conformity')

            self.api_key = os.environ['CC_API_KEY']
            self.cfn_template_file_location = os.environ['CFN_TEMPLATE_FILE_LOCATION']
            risk_level = os.getenv('CC_RISK_LEVEL', 'LOW').upper()

        except KeyError:
            sys.exit('Error: Please ensure all environment variables are set')

        try:
            self.offending_risk_level_num = RISK_LEVEL_NUMS[risk_level]

        except KeyError:
            sys.exit('Error: Unknown risk level. Please use one of LOW | MEDIUM | HIGH | VERY_HIGH | EXTREME')

        print(f'All environment variables were received. The pipeline will fail if any "{risk_level}" level '
              f'issues are found')

    def generate_payload(self):
        try:
            with open(self.cfn_template_file_location, 'r') as f:
                cfn_contents = f.read()

                payload = {
                    'data': {
                        'attributes': {
                            'type': 'cloudformation-template',
                            'contents': cfn_contents
                        }
                    }
                }

        except FileNotFoundError as e:
            sys.exit(f'Error: {e}')

        return payload

    def run_validation(self, payload):
        cfn_scan_endpoint = f'https://{self.cc_region}-api.cloudconformity.com/v1/iac-scanning/scan'

        json_output = json.dumps(payload, indent=4, sort_keys=True)
        print(f'Request:\n{json_output}')

        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Authorization': 'ApiKey ' + self.api_key
        }

        resp = requests.post(cfn_scan_endpoint, headers=headers, data=json_output)
        resp_json = json.loads(resp.text)
        json_output = json.dumps(resp_json, indent=4, sort_keys=True)
        print(f'Response:\n{json_output}')

        return resp_json

    def check_results(self, findings):
        offending_entries = []

        for entry in findings['data']:
            risk_level_text = entry['attributes']['risk-level']
            risk_level_num = RISK_LEVEL_NUMS[risk_level_text]

            if risk_level_num >= self.offending_risk_level_num:
                offending_entries.append(entry)

        return offending_entries


def main():
    cc = CcValidator()
    payload = cc.generate_payload()
    findings = cc.run_validation(payload)
    offending_entries = cc.check_results(findings)

    if not offending_entries:
        print('\nNo offending entries found')
        sys.exit()

    num_offending_entries = len(offending_entries)
    json_offending_entries = json.dumps(offending_entries, indent=4, sort_keys=True)
    print(f'Offending entries:\n{json_offending_entries}')
    print(f'\nError: {num_offending_entries} offending entries found')
    sys.exit(1)


if __name__ == '__main__':
    main()
