# Build the application from source
FROM golang:1.21-bookworm AS build-stage

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /rafs-cronjob

# Deploy the application binary into a lean image
FROM gcr.io/distroless/base-debian12 AS build-release-stage

WORKDIR /

COPY --from=build-stage /rafs-cronjob /rafs-cronjob

USER nonroot:nonroot

ENTRYPOINT ["/rafs-cronjob"]