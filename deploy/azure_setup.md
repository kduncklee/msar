# Bamru Azure setup - inital runbook

## Preliminary steps

* Install `az` (e.g. `pip install azure-cli`)
* `az login`
* `az extension add --name db-up`
  * On MacOS the system's Python 3.9 is not compatible. You may need to install your own.
* Install `pqsl` (e.g. `postgresql-client` package)

## Prepare data
Ensure the following are present in the `deploy` directory:
* `db.sql.gz` (if doing DB import)
* `azure_secrets.json`

## Initial setup

### Generate a strong password for postgres
Do this however you like best.

## Set up everything other than the certificate:
`SETUP_AZ=true SETUP_STORE=true SETUP_DB=true SETUP_CONFIG=true ./azure_setup.sh bamrunet bamru.info 'XXX_MAIN_DATABASE_PASSWORD_XXX' 'XXX_READONLY_DATABASE_PASSWORD_XXX'`

You may want to run each SETUP_x step sequentially to verify.

## Upload storage data (optional - if migrating from another platform)
Log into prod, enter the vagrant vm, become bamru user

`cd ~bamru/system`

Then...

**option 1:**
* `az login`
* `sudo az storage blob upload-batch -d media -s . --account-name bamrunet --account-key ''`
  * Yes, this command has an empty account key. It's correct.
  * (ignore warnings that it is looking up account key)

**option 2:**
* copy and run the storage command from the azure_setup output

## Cert setup
Go to namecheap and set:
  * A record of root to prod IP
  * CNAME of staging to staging hostname (bamrunet-app-staging.azurewebsites.net)
  * asuid and asuid.staging TXT records containing b1f53b6f370f9f357a1da8e1c3e8c61795d7deefc09440c65fb3e21f9ed6be9d

`SETUP_CERT=true ./azure_setup.sh bamrunet bamru.info bogus_unused_database_password bogus_unused_database_password`
`SETUP_CERT_SLOT=true ./azure_setup.sh bamrunet bamru.info bogus_unused_database_password bogus_unused_database_password`

It will take some time for thumbnails to be done. If you see 'Conflict', just wait a bit and try again.

If you get other errors, check the namecheap config and/or try in the GUI for better messages.
You can also add --debug to the azure CLI command. The TXT record may have changed. You can find the "Custom Domain Verification ID" under "bamrunet-app | Custom domains".

## Deployment from github
* Go to "Deployment Center" in app/staging on portal.azure.com
* Select GitHub
* Authorize
* "Manage publish profile" -> Download
* Go to the github repo -> github.com/.../settings/secrets/actions
* Save the downloaded file as AZUREAPPSERVICE_PUBLISHPROFILE
* Do the same for the dev webapp and save as AZUREAPPSERVICE_PUBLISHPROFILE_DEV

* Save the output of this as AZURE_CREDENTIALS:
az ad sp create-for-rbac --name "bamrunet-ad-sp" --role contributor \
    --scopes /subscriptions/{subscription-id}/resourceGroups/bamrunet-rg \
    --sdk-auth
