from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "airbnb-bigdata-app") -> SparkSession:
    """Create a Spark session for local analytics and ML workloads."""
    spark = (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark
