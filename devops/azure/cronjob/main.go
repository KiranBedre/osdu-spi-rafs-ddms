/*
#  Copyright 2023 ExxonMobil Technology and Engineering Company
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
*/

package main

import (
	"context"
	"crypto/tls"
	"fmt"
	"log"
	"log/slog"
	"net/http"
	"os"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets"

	retry "github.com/avast/retry-go"
)

/*
References:
  https://learn.microsoft.com/en-us/azure/key-vault/secrets/quick-create-go?source=recommendations
*/

const (
	azure_oauth_appid_secret           = "aad-client-id"
	azure_oauth_client_id_secret       = "app-dev-sp-username"
	azure_oauth_client_password_secret = "app-dev-sp-password"
	azure_oauth_tenant_secret          = "tenant-id"
	// Rafs endpoints
	record_index_endpoint = "api/rafs-ddms/dev/sa_records_index"
	expected_code         = 200
)

func _get_auth_parameters(vault_uri string) (*azidentity.ClientSecretCredential, *policy.TokenRequestOptions, error) {
	return_creds := azidentity.ClientSecretCredential{}
	token_request_options := policy.TokenRequestOptions{}
	// Create a credential using the NewDefaultAzureCredential type.
	cred, err := azidentity.NewDefaultAzureCredential(nil)
	if err != nil {
		return &return_creds, &token_request_options, err
	}

	// Establish a connection to the Key Vault client
	client, err := azsecrets.NewClient(vault_uri, cred, nil)
	if err != nil {
		return &return_creds, &token_request_options, err
	}

	version := ""
	azure_client_id, err := client.GetSecret(context.TODO(), azure_oauth_client_id_secret, version, nil)
	if err != nil {
		return &return_creds, &token_request_options, err
	}
	azure_client_secret, err := client.GetSecret(context.TODO(), azure_oauth_client_password_secret, version, nil)
	if err != nil {
		return &return_creds, &token_request_options, err
	}
	azure_appid, err := client.GetSecret(context.TODO(), azure_oauth_appid_secret, version, nil)
	if err != nil {
		return &return_creds, &token_request_options, err
	}
	tenant_id, err := client.GetSecret(context.TODO(), azure_oauth_tenant_secret, version, nil)
	if err != nil {
		return &return_creds, &token_request_options, err
	}

	client_creds, err := azidentity.NewClientSecretCredential(*tenant_id.Value, *azure_client_id.Value, *azure_client_secret.Value, &azidentity.ClientSecretCredentialOptions{})
	if err != nil {
		return &return_creds, &token_request_options, err
	}
	token_request_options.Scopes = []string{
		fmt.Sprintf("%s/.default", *azure_appid.Value),
	}
	token_request_options.EnableCAE = false
	token_request_options.TenantID = *tenant_id.Value
	slog.Info("Retrieved access secrets correctly")
	return client_creds, &token_request_options, nil
}

func main() {
	vault_uri := os.Getenv("AZURE_KEY_VAULT_URI")
	rafs_uri := os.Getenv("RAFS_URI")
	if len(vault_uri) < 3 {
		log.Fatal("no (AZURE_KEY_VAULT_URI) env var")
	}
	if len(rafs_uri) < 3 {
		log.Fatal("no (RAFS_URI) env var")
	}
	azure_sa, token_options, err := _get_auth_parameters(vault_uri)
	if err != nil {
		log.Fatal(err)
	}
	slog.Info("Retrieving service account token")
	access_token, err := azure_sa.GetToken(context.Background(), *token_options)
	if err != nil {
		log.Fatal(err)
	}

	rafs_reindex_url := fmt.Sprintf("%s/%s", rafs_uri, record_index_endpoint)
	slog.Info(fmt.Sprintf("GET %s", rafs_reindex_url))

	http.DefaultTransport.(*http.Transport).TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	req, err := http.NewRequest("GET", rafs_reindex_url, nil)
	if err != nil {
		log.Fatal(err)
	}
	req.Header.Add("Authorization", fmt.Sprintf("Bearer %s", access_token.Token))
	req.Header.Add("data-partition-id", "opendes")

	err = retry.Do(
		func() error {
			c := http.Client{}
			res, err := c.Do(req)
			if err != nil {
				return err
			}
			slog.Info(fmt.Sprintf("Response Code: %d", res.StatusCode))
			if res.StatusCode != expected_code {
				new_err := fmt.Errorf("unexpected response code %d != %d", res.StatusCode, expected_code)
				return new_err
			}
			res.Body.Close()
			return nil
		},
		retry.Attempts(5),
		retry.Delay(4*time.Second),
		retry.OnRetry(func(n uint, err error) {
			slog.Warn(fmt.Sprintf("retry #%d: %s\n", n, err))
		}),
	)

	if err != nil {
		log.Fatal(err)
	}
}
