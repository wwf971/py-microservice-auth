a simple jwt-based authentication microservice written in python.


```
docker-auth/
├── src/
│   ├── auth.proto              # gRPC service definition
│   ├── main.py                 # gRPC server entry point
│   ├── auth_service.py         # Authentication logic
│   └── requirementsA.txt       # Python dependencies
├── Dockerfile                  # Docker configuration
├── compile_proto.sh            # Compile protobuf files
├── run_local.sh                # Run server locally
├── build_and_run.sh            # Build and run Docker container
├── test_client.py              # Test client example
└── README.md                   # This file
```
