# Tool Paths

Local tool installations not in default PATH.

## BigQuery CLI

- **bq**: `/Users/bonnie/Downloads/google-cloud-sdk/bin/bq`
- **gcloud**: `/Users/bonnie/Downloads/google-cloud-sdk/bin/gcloud`
- **SDK root**: `/Users/bonnie/Downloads/google-cloud-sdk`

For any bash command using `bq` or `gcloud`, prepend the SDK bin to PATH first:

```bash
export PATH="/Users/bonnie/Downloads/google-cloud-sdk/bin:$PATH" && bq ...
```

Or use absolute paths directly.

## BQ Projects

| Project ID | Environment |
|------------|-------------|
| `gru-dp-dev/uat/prod` | GRU Data Platform |
| `won-dp-dev/uat/prod` | Wonder Data Platform |
| `won-ful-dev/uat/prod` | Wonder Fulfillment |
| `won-merch-dev/uat/prod` | Wonder Merchandise |
| `won-oms-dev/uat/prod` | Wonder OMS |
| `won-billing-export` | Billing Export |

Account: `bonnieyang@xm.wonder.com`
