import logging, math

def fit(X, Y):

    def mean(Xs):
        return sum(Xs) / len(Xs)

    def std(Xs, m):
        normalizer = len(Xs) - 1
        return math.sqrt(sum((pow(x - m, 2) for x in Xs)) / normalizer)

    sum_xy = 0
    sum_sq_v_x = 0
    sum_sq_v_y = 0
    sum_sq_x = 0

    m_X = mean(X)
    m_Y = mean(Y)

    for (x, y) in zip(X, Y):
        var_x = x - m_X
        var_y = y - m_Y
        sum_xy += var_x * var_y
        sum_sq_v_x += pow(var_x, 2)
        sum_sq_v_y += pow(var_y, 2)
        sum_sq_x += pow(x, 2)

    # Number of data points
    n = len(X)
    logging.info("n: %d" % n)

    # Pearson R
    r = sum_xy / math.sqrt(sum_sq_v_x * sum_sq_v_y)

    # Slope
    m = r * (std(Y, m_Y) / std(X, m_X))

    # Intercept
    b = m_Y - m * m_X

    logging.info("m: %f" % m)
    logging.info("b: %f" % b)
    logging.info("r: %f" % r)

    # Estimate measurement error from resuduals
    sum_res_sq = 0
    for (x, y) in zip(X, Y):
        res = m*x + b - y
        sum_res_sq += pow(res,2)
    logging.info("sum_res_sq: %f" % sum_res_sq)
    logging.info("sum_sq_v_x: %f" % sum_sq_v_x)
    logging.info("sum_sq_x: %f" % sum_sq_x)

    # Error on slope
    if n > 2 and sum_res_sq > 0 :
      sm = math.sqrt(1./(n-2) * sum_res_sq / sum_sq_v_x)
    else :
      sm = 0
    logging.info("sm: %f" % sm)

    # Error on intercept
    sb = sm * math.sqrt(1./n * sum_sq_x)
    logging.info("sb: %f" % sb)

    return [m,b,r,sm,sb]

