/**
 * Routes for product-related operations
 * @description Routes for product-related operations
 */

import { Router } from "express";
import { searchProducts } from "../controllers/productController.js";

const router = Router();

router.get("/search", searchProducts);

export default router;
