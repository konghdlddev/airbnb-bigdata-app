from pyspark.ml import PipelineModel
from pyspark.ml.evaluation import RegressionEvaluator

from configs.settings import settings
from configs.spark_session import get_spark_session


if __name__ == "__main__":
    """Evaluate the trained model on a holdout split."""
    spark = get_spark_session("airbnb-evaluate-price-model")

    df = spark.read.parquet(settings.gold_data_path).select(
        "room_type",
        "neighbourhood",
        "minimum_nights",
        "number_of_reviews",
        "reviews_per_month",
        "availability_365",
        "price",
    )

    _, test_df = df.randomSplit([0.8, 0.2], seed=42)
    model = PipelineModel.load(settings.model_local_path)
    pred_df = model.transform(test_df)

    rmse = RegressionEvaluator(labelCol="price", predictionCol="prediction", metricName="rmse").evaluate(
        pred_df
    )
    mae = RegressionEvaluator(labelCol="price", predictionCol="prediction", metricName="mae").evaluate(
        pred_df
    )
    r2 = RegressionEvaluator(labelCol="price", predictionCol="prediction", metricName="r2").evaluate(
        pred_df
    )

    print(f"RMSE: {rmse:.2f}")
    print(f"MAE: {mae:.2f}")
    print(f"R2: {r2:.4f}")

    spark.stop()
