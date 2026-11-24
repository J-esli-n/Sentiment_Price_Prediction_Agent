    model = _new_model()
    model.fit(x, y)
    latest = frame.dropna(subset=FEATURE_COLUMNS).iloc[-1:]
    predicted_return = float(model.predict(latest[FEATURE_COLUMNS].astype(float))[0])
    current_price = float(latest["close"].iloc[0])