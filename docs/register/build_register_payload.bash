#!/bin/bash

function _build_register_payload() {
  if [ -z RAFS_URL ]; then echo "[ERROR] Need RAFS_URL to get openapi spec"; exit 1; fi

  export TEMP_DIR=$(mktemp -d)

  ENTITIES=(rocksampleanalysis coring rocksample)
  # To add new entity id add in this line
  for entity in ${ENTITIES[@]}; do
    PATHS_OUT=$(curl ${RAFS_URL}/api/rafs-ddms/openapi.json | jq -r --arg ENTITY "$entity/{record_id}" \
      '.paths | to_entries | [.[] | select((.key | endswith($ENTITY)) and (.value | has("get")))] |
       .[].value.get += {"x-ddms-retrieve-entity": true} | del(.[].value.delete) | from_entries')
    cat <<EOF > ${TEMP_DIR}/${entity}.json
{
        "entityType": "${entity}",
        "schema": {
            "openapi": "3.0.0",
            "info": {
              "title": "Rock and Sample Fluid DDMS",
              "version": "0.1.0"
          },
            "servers": [
                {
                    "url": "${RAFS_URL}"
                }
            ],
            "tags": [
                {
                    "name": "rafs",
                    "description": "Rock And Fluid Sample DDMS",
                    "openspec": "https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/docs/api/community/v2/openapi.yaml"
                }
            ],
             "paths": ${PATHS_OUT}              
        }
    }
EOF
    #cat ${TEMP_DIR}/${entity}.json
    echo "[INFO] Build --- ${TEMP_DIR}/${entity}.json"
  done

  # Join all interfaces in one single file
  jq -r -s '[.[0],.[1],.[2]]' $(for ii in ${ENTITIES[@]}; do echo "${TEMP_DIR}/${ii}.json"; done | xargs) > ${TEMP_DIR}/interfaces.json
  # Build the final payload
  jq -s '{ "id": "rafs", "name": "rafsDDMS","description": "Rock And Fluid Sample DDMS","contactEmail": "osdu-sre@osdu.com", "interfaces": .[0]}' ${TEMP_DIR}/interfaces.json > ${TEMP_DIR}/rafsddms_register.json
  # Substitute the RAFS_URL
  sed -i "s;{{OSDU_URL}};$RAFS_URL;g" ${TEMP_DIR}/rafsddms_register.json

  echo ${TEMP_DIR}/rafsddms_register.json
}
