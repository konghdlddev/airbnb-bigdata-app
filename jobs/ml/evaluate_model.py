import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pyspark.ml import PipelineModel
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql import functions as F

from configs.settings import settings
from configs.spark_session import get_spark_session
from jobs.ml.train_price_model import prepare_gold_for_ml


if __name__ == "__main__":
    """Evaluate the trained model on the same holdout split as training (same preprocessing)."""
    spark = get_spark_session("airbnb-evaluate-price-model")

    df, _ = prepare_gold_for_ml(spark)
    _, test_df = df.randomSplit([0.8, 0.2], seed=42)
    model = PipelineModel.load(settings.model_local_path)
    pred_df = model.transform(test_df)
    # Model predicts log(price); convert back to price for metrics.
    pred_df = pred_df.withColumn("predicted_price", F.exp(F.col("prediction")))

    rmse = RegressionEvaluator(labelCol="price", predictionCol="predicted_price", metricName="rmse").evaluate(
        pred_df
    )
    mae = RegressionEvaluator(labelCol="price", predictionCol="predicted_price", metricName="mae").evaluate(
        pred_df
    )
    r2 = RegressionEvaluator(labelCol="price", predictionCol="predicted_price", metricName="r2").evaluate(
        pred_df
    )

    print(f"RMSE: {rmse:.2f}")
    print(f"MAE: {mae:.2f}")
    print(f"R2: {r2:.4f}")

    spark.stop()
