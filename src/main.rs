use temporal_db::{initialize_temporal_database, SpecificationRecord, SpecificationType};

#[tokio::main]
async fn main() {
    println!("Initializing VibesPro Temporal Database...");

    // Example usage of the temporal database
    match initialize_temporal_database("./temporal_data.tsinkdb").await {
        Ok(mut repo) => {
            println!("Temporal database initialized successfully!");

            // Create a sample specification
            let spec = SpecificationRecord::new(
                SpecificationType::ADR,
                "ADR-MERGE-001".to_string(),
                "Generator-First Architecture Decision".to_string(),
                "We choose a generator-first approach for maximum code reuse...".to_string(),
                Some("system".to_string()),
            );

            if let Err(e) = repo.store_specification(&spec).await {
                eprintln!("Failed to store specification: {}", e);
            } else {
                println!("Sample specification stored successfully!");
            }

            if let Err(e) = repo.close().await {
                eprintln!("Failed to close database: {}", e);
            }
        }
        Err(e) => {
            eprintln!("Failed to initialize temporal database: {}", e);
        }
    }
}
