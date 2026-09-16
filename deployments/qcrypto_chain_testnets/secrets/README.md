# Deployment secrets

Do not commit secret material to this directory.

The observer Compose package expects only `engine-jwt.hex`, used to authenticate the Ethereum execution/consensus Engine API connection. Generate it on the target host, keep it owner-readable only, and never reuse it as a wallet, validator, withdrawal, or signing key.

This package intentionally contains no Bitcoin wallet key, Ethereum validator key, seed phrase, keystore, withdrawal credential, or HSM credential.
