/**
 * Error handler middleware
 * @param {*} err
 * @param {*} req
 * @param {*} res
 * @param {*} next
 */
export function errorHandler(err, req, res, next) {
  console.error(err.stack);

  const status = err.status ?? 500;
  const message =
    process.env.NODE_ENV === "production"
      ? "Something went wrong"
      : err.message;

  res.status(status).json({ error: message });
}
