# Simple math helper functions
#
# Copyright (C) 2018-2019  Kevin O'Connor <kevin@koconnor.net>
# Copyright (C) 2025-2026  Dmitry Butyugin <dmbutyugin@google.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import copy, math, logging, multiprocessing, traceback
import queuelogger


######################################################################
# Coordinate descent
######################################################################

# Helper code that implements coordinate descent
def coordinate_descent(adj_params, params, error_func):
    # Define potential changes
    params = dict(params)
    dp = {param_name: 1. for param_name in adj_params}
    # Calculate the error
    best_err = error_func(params)
    logging.info("Coordinate descent initial error: %s", best_err)

    threshold = 0.00001
    rounds = 0

    while sum(dp.values()) > threshold and rounds < 10000:
        rounds += 1
        for param_name in adj_params:
            orig = params[param_name]
            params[param_name] = orig + dp[param_name]
            err = error_func(params)
            if err < best_err:
                # There was some improvement
                best_err = err
                dp[param_name] *= 1.1
                continue
            params[param_name] = orig - dp[param_name]
            err = error_func(params)
            if err < best_err:
                # There was some improvement
                best_err = err
                dp[param_name] *= 1.1
                continue
            params[param_name] = orig
            dp[param_name] *= 0.9
    logging.info("Coordinate descent best_err: %s  rounds: %d",
                 best_err, rounds)
    return params

# Helper to run the coordinate descent function in a background
# process so that it does not block the main thread.
def background_coordinate_descent(printer, adj_params, params, error_func):
    parent_conn, child_conn = multiprocessing.Pipe()
    def wrapper():
        queuelogger.clear_bg_logging()
        try:
            res = coordinate_descent(adj_params, params, error_func)
        except:
            child_conn.send((True, traceback.format_exc()))
            child_conn.close()
            return
        child_conn.send((False, res))
        child_conn.close()
    # Start a process to perform the calculation
    calc_proc = multiprocessing.Process(target=wrapper)
    calc_proc.daemon = True
    calc_proc.start()
    # Wait for the process to finish
    reactor = printer.get_reactor()
    gcode = printer.lookup_object("gcode")
    eventtime = last_report_time = reactor.monotonic()
    while calc_proc.is_alive():
        if eventtime > last_report_time + 5.:
            last_report_time = eventtime
            gcode.respond_info("Working on calibration...", log=False)
        eventtime = reactor.pause(eventtime + .1)
    # Return results
    is_err, res = parent_conn.recv()
    if is_err:
        raise Exception("Error in coordinate descent: %s" % (res,))
    calc_proc.join()
    parent_conn.close()
    return res


######################################################################
# Trilateration
######################################################################

# Trilateration finds the intersection of three spheres.  See the
# wikipedia article for the details of the algorithm.
def trilateration(sphere_coords, radius2):
    sphere_coord1, sphere_coord2, sphere_coord3 = sphere_coords
    s21 = matrix_sub(sphere_coord2, sphere_coord1)
    s31 = matrix_sub(sphere_coord3, sphere_coord1)

    d = math.sqrt(matrix_magsq(s21))
    ex = matrix_mul(s21, 1. / d)
    i = matrix_dot(ex, s31)
    vect_ey = matrix_sub(s31, matrix_mul(ex, i))
    ey = matrix_mul(vect_ey, 1. / math.sqrt(matrix_magsq(vect_ey)))
    ez = matrix_cross(ex, ey)
    j = matrix_dot(ey, s31)

    x = (radius2[0] - radius2[1] + d**2) / (2. * d)
    y = (radius2[0] - radius2[2] - x**2 + (x-i)**2 + j**2) / (2. * j)
    z = -math.sqrt(radius2[0] - x**2 - y**2)

    ex_x = matrix_mul(ex, x)
    ey_y = matrix_mul(ey, y)
    ez_z = matrix_mul(ez, z)
    return matrix_add(sphere_coord1, matrix_add(ex_x, matrix_add(ey_y, ez_z)))


######################################################################
# Matrix helper functions for 3x1 matrices
######################################################################

def matrix_cross(m1, m2):
    return [m1[1] * m2[2] - m1[2] * m2[1],
            m1[2] * m2[0] - m1[0] * m2[2],
            m1[0] * m2[1] - m1[1] * m2[0]]

def matrix_dot(m1, m2):
    return m1[0] * m2[0] + m1[1] * m2[1] + m1[2] * m2[2]

def matrix_magsq(m1):
    return m1[0]**2 + m1[1]**2 + m1[2]**2

def matrix_add(m1, m2):
    return [m1[0] + m2[0], m1[1] + m2[1], m1[2] + m2[2]]

def matrix_sub(m1, m2):
    return [m1[0] - m2[0], m1[1] - m2[1], m1[2] - m2[2]]

def matrix_mul(m1, s):
    return [m1[0]*s, m1[1]*s, m1[2]*s]

######################################################################
# Matrix helper functions for NxM matrices
######################################################################

def mat_mat_mul(a, b):
    if len(a[0]) != len(b):
        return None
    res = []
    for i in range(len(a)):
        res.append([])
        for j in range(len(b[0])):
            res[i].append(sum(a[i][k] * b[k][j] for k in range(len(b))))
    return res

def mat_transp(a):
    res = []
    for i in range(len(a[0])):
        res.append([a[j][i] for j in range(len(a))])
    return res

def gaussian_solve(a, rhs):
    res = copy.deepcopy(rhs)
    m = copy.deepcopy(a)
    n = len(m)
    # Perform the LU-decomposition through Gaussian elimination
    for i in range(n):
        # Find a pivot and swap the corresponding rows
        abs_col = [abs(m[j][i]) for j in range(i, n)]
        j = abs_col.index(max(abs_col)) + i
        if i != j:
            m[i], m[j] = m[j], m[i]
            res[i], res[j] = res[j], res[i]

        if abs(m[i][i]) < 1e-10:
            return None
        # Scale the i-th row
        recipr = 1. / m[i][i]
        for j in range(i+1, n):
            m[i][j] *= recipr
        for j in range(len(res[i])):
            res[i][j] *= recipr
        m[i][i] = 1.

        # Zero-out the i-th column after the row i
        for j in range(i+1, n):
            c = m[j][i]
            for k in range(i, n):
                m[j][k] -= c * m[i][k]
            for k in range(len(res[j])):
                res[j][k] -= c * res[i][k]

    # Solve the system with the upper-triangular matrix
    for i in range(n-2, -1, -1):
        for j in range(i+1, n):
            for k in range(len(res[j])):
                res[i][k] -= m[i][j] * res[j][k]
    return res

def pseudo_inverse(m):
    mt = mat_transp(m)
    mtm = mat_mat_mul(mt, m)
    return gaussian_solve(mtm, mt)

######################################################################
# Simple statistics
######################################################################

# Standard deviation (square-root of variance) of the given samples
def std(samples) :
    mean = 0.
    for v in samples :
      mean += v/float(len(samples))
    variance = 0.
    for v in samples :
      variance += (v-mean)**2
    return math.sqrt(variance)

######################################################################
# Linear regression helper function
######################################################################

def linear_regression(X, Y, extra_err=0):

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

    # Pearson R
    r = sum_xy / math.sqrt(sum_sq_v_x * sum_sq_v_y)

    # Slope
    m = r * (std(Y, m_Y) / std(X, m_X))

    # Intercept
    b = m_Y - m * m_X

    # Estimate measurement error from resuduals
    sum_res_sq = 0
    for (x, y) in zip(X, Y):
        res = m*x + b - y + extra_err
        sum_res_sq += pow(res,2)

    # Error on slope
    if n > 2 and sum_res_sq > 0 :
      sm = math.sqrt(1./(n-2) * sum_res_sq / sum_sq_v_x)
    elif sum_res_sq > 0 :
      sm = math.sqrt(sum_res_sq / sum_sq_v_x)
    else :
      sm = 0

    # Error on intercept
    sb = sm * math.sqrt(1./n * sum_sq_x)

    return [m,b,r,sm,sb]
