/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.6.23-MariaDB, for debian-linux-gnu (aarch64)
--
-- Host: 127.0.0.1    Database: db_huawei
-- ------------------------------------------------------
-- Server version	10.6.23-MariaDB-0ubuntu0.22.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Camera`
--

DROP TABLE IF EXISTS `Camera`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `Camera` (
  `id_cam` varchar(20) NOT NULL,
  `Status` varchar(50) DEFAULT NULL,
  `id_gejala` varchar(20) NOT NULL,
  `Tanggal` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_cam`),
  KEY `id_gejala` (`id_gejala`),
  CONSTRAINT `Camera_ibfk_1` FOREIGN KEY (`id_gejala`) REFERENCES `Gejala` (`id_gejala`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Camera`
--

LOCK TABLES `Camera` WRITE;
/*!40000 ALTER TABLE `Camera` DISABLE KEYS */;
INSERT INTO `Camera` VALUES ('C0000000000000000001','mengantuk','G0000000000000000001','2026-11-01 09:40:00'),('C0000000000000000002','merah','G0000000000000000003','2026-11-08 08:10:00'),('C0000000000000000003','bengkak','G0000000000000000004','2026-11-10 19:55:00');
/*!40000 ALTER TABLE `Camera` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Gejala`
--

DROP TABLE IF EXISTS `Gejala`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `Gejala` (
  `id_gejala` varchar(20) NOT NULL,
  `NIK` varchar(16) NOT NULL,
  `Batuk` varchar(20) DEFAULT NULL,
  `Suhu` float DEFAULT NULL,
  `Tanggal` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_gejala`),
  KEY `NIK` (`NIK`),
  CONSTRAINT `Gejala_ibfk_1` FOREIGN KEY (`NIK`) REFERENCES `Users` (`NIK`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Gejala`
--

LOCK TABLES `Gejala` WRITE;
/*!40000 ALTER TABLE `Gejala` DISABLE KEYS */;
INSERT INTO `Gejala` VALUES ('G0000000000000000001','3201234567890002','kering',38.5,'2026-11-01 09:30:00'),('G0000000000000000002','3201234567890002','berdahak',39,'2026-11-05 14:10:00'),('G0000000000000000003','3201234567890003',NULL,37.2,'2026-11-08 08:00:00'),('G0000000000000000004','3201234567890004','parah',40,'2026-11-10 19:45:00');
/*!40000 ALTER TABLE `Gejala` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Role`
--

DROP TABLE IF EXISTS `Role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `Role` (
  `id_Role` varchar(10) NOT NULL,
  `Name` varchar(50) NOT NULL,
  PRIMARY KEY (`id_Role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Role`
--

LOCK TABLES `Role` WRITE;
/*!40000 ALTER TABLE `Role` DISABLE KEYS */;
INSERT INTO `Role` VALUES ('R1','Admin'),('R2','User');
/*!40000 ALTER TABLE `Role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Status`
--

DROP TABLE IF EXISTS `Status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `Status` (
  `id_rept` varchar(20) NOT NULL,
  `id_cam` varchar(20) NOT NULL,
  PRIMARY KEY (`id_rept`),
  KEY `id_cam` (`id_cam`),
  CONSTRAINT `Status_ibfk_1` FOREIGN KEY (`id_cam`) REFERENCES `Camera` (`id_cam`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Status`
--

LOCK TABLES `Status` WRITE;
/*!40000 ALTER TABLE `Status` DISABLE KEYS */;
INSERT INTO `Status` VALUES ('R0000000000000000001','C0000000000000000001'),('R0000000000000000002','C0000000000000000002');
/*!40000 ALTER TABLE `Status` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Users`
--

DROP TABLE IF EXISTS `Users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `Users` (
  `NIK` varchar(16) NOT NULL,
  `Name` varchar(100) NOT NULL,
  `Tempat_Tgl_Lahir` varchar(150) DEFAULT NULL,
  `Golongan_darah` varchar(2) DEFAULT NULL,
  `Email` varchar(255) DEFAULT NULL,
  `Alamat` text DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `id_Role` varchar(10) NOT NULL,
  PRIMARY KEY (`NIK`),
  UNIQUE KEY `Email` (`Email`),
  KEY `id_Role` (`id_Role`),
  CONSTRAINT `Users_ibfk_1` FOREIGN KEY (`id_Role`) REFERENCES `Role` (`id_Role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Users`
--

LOCK TABLES `Users` WRITE;
/*!40000 ALTER TABLE `Users` DISABLE KEYS */;
INSERT INTO `Users` VALUES ('3201234567890002','Bagas Pratama','Bandung, 1998-03-12','O','bagas@example.com','Jl. Merdeka No. 1, Bandung','$2b$12$2bJ9ijbB6P4hhKrDFMc4TOGbL49P2qLGOKq0KHWcIsclbHgiIFwfS','R2'),('3201234567890003','Siti Rahayu','Jakarta, 2001-07-25','A','siti@example.com','Jl. Sudirman No. 45, Jakarta','$2b$12$FHciUvjKIltwyxGnm0euKeg5tzwVK8FnKb0PHUaMFAPoiVBKuJVw6','R2'),('3201234567890004','Dewi Lestari','Surabaya, 1995-11-02','B','dewi@example.com','Jl. Pemuda No. 8, Surabaya','$2b$12$YvVReF3ikhmfdBW1/5d1Uu4G9194.vhNfHJZWkTEPZIGcbq/ds0H.','R2'),('admin','Administrator','-',NULL,NULL,'-','$2b$12$.8SQj/3ROTaQnnGNM3SF.OLxIpWG8Pii5WaSPSjpLzWSxaEdZI5US','R1');
/*!40000 ALTER TABLE `Users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `aturan_pakar`
--

DROP TABLE IF EXISTS `aturan_pakar`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `aturan_pakar` (
  `id_aturan` varchar(20) NOT NULL,
  `nama_aturan` varchar(150) NOT NULL,
  `kesimpulan` varchar(150) NOT NULL,
  `prioritas` int(11) NOT NULL,
  `keterangan` text DEFAULT NULL,
  `aktif` tinyint(1) NOT NULL,
  PRIMARY KEY (`id_aturan`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `aturan_pakar`
--

LOCK TABLES `aturan_pakar` WRITE;
/*!40000 ALTER TABLE `aturan_pakar` DISABLE KEYS */;
INSERT INTO `aturan_pakar` VALUES ('R01','Clinical Pattern - Batuk','CLINICAL_MEASLES_PATTERN',1,'Demam, ruam makulopapular, dan batuk.',1),('R02','Clinical Pattern - Pilek','CLINICAL_MEASLES_PATTERN',1,'Demam, ruam makulopapular, dan pilek.',1),('R03','Clinical Pattern - Konjungtivitis','CLINICAL_MEASLES_PATTERN',1,'Demam, ruam makulopapular, dan konjungtivitis.',1),('R04','Suspected Case-Finding Pattern','SUSPECTED_CASE_FINDING_PATTERN',2,'Demam, ruam makulopapular, dan ruam menyeluruh.',1),('R05A','Safety Alert - Kesulitan Bernapas','SAFETY_ALERT',1,'Pasien mengalami kesulitan bernapas.',1),('R05B','Safety Alert - Kejang','SAFETY_ALERT',1,'Pasien mengalami kejang.',1),('R05C','Safety Alert - Penurunan Kesadaran','SAFETY_ALERT',1,'Pasien mengalami penurunan kesadaran.',1);
/*!40000 ALTER TABLE `aturan_pakar` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `aturan_pakar_detail`
--

DROP TABLE IF EXISTS `aturan_pakar_detail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `aturan_pakar_detail` (
  `id_detail` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_aturan` varchar(20) NOT NULL,
  `kode_gejala` varchar(30) NOT NULL,
  `operator_kondisi` enum('=','>','<','>=','<=') NOT NULL,
  `nilai_kondisi` varchar(50) NOT NULL,
  PRIMARY KEY (`id_detail`),
  KEY `id_aturan` (`id_aturan`),
  KEY `kode_gejala` (`kode_gejala`),
  CONSTRAINT `aturan_pakar_detail_ibfk_1` FOREIGN KEY (`id_aturan`) REFERENCES `aturan_pakar` (`id_aturan`),
  CONSTRAINT `aturan_pakar_detail_ibfk_2` FOREIGN KEY (`kode_gejala`) REFERENCES `master_gejala` (`kode_gejala`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `aturan_pakar_detail`
--

LOCK TABLES `aturan_pakar_detail` WRITE;
/*!40000 ALTER TABLE `aturan_pakar_detail` DISABLE KEYS */;
INSERT INTO `aturan_pakar_detail` VALUES (1,'R01','DEMAM','=','1'),(2,'R01','RUAM','=','1'),(3,'R01','BATUK','=','1'),(4,'R02','DEMAM','=','1'),(5,'R02','RUAM','=','1'),(6,'R02','PILEK','=','1'),(7,'R03','DEMAM','=','1'),(8,'R03','RUAM','=','1'),(9,'R03','MATA_MERAH','=','1'),(10,'R04','DEMAM','=','1'),(11,'R04','RUAM','=','1'),(12,'R04','RUAM_MENYELURUH','=','1'),(13,'R05A','SESAK','=','1'),(14,'R05B','KEJANG','=','1'),(15,'R05C','PENURUNAN_KESADARAN','=','1');
/*!40000 ALTER TABLE `aturan_pakar_detail` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evidence_reconciliations`
--

DROP TABLE IF EXISTS `evidence_reconciliations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `evidence_reconciliations` (
  `id_reconciliation` varchar(36) NOT NULL,
  `id_gejala` varchar(20) NOT NULL,
  `reconciliation_status` varchar(20) NOT NULL,
  `summary` varchar(255) NOT NULL,
  `cv_status` varchar(20) NOT NULL,
  `temp_status` varchar(20) NOT NULL,
  `expert_status` varchar(20) NOT NULL,
  `cv_prediction` varchar(50) DEFAULT NULL,
  `cv_confidence` float DEFAULT NULL,
  `measured_temp` float DEFAULT NULL,
  `expert_category` varchar(100) DEFAULT NULL,
  `safety_alert` tinyint(1) NOT NULL,
  `supporting_evidence` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`supporting_evidence`)),
  `conflicting_evidence` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`conflicting_evidence`)),
  `missing_evidence` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`missing_evidence`)),
  `invalid_evidence` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`invalid_evidence`)),
  `explanation` text NOT NULL,
  `recommended_action` text NOT NULL,
  `rule_version` varchar(20) NOT NULL,
  `is_diagnosis` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_reconciliation`),
  UNIQUE KEY `ix_evidence_reconciliations_id_gejala` (`id_gejala`),
  CONSTRAINT `evidence_reconciliations_ibfk_1` FOREIGN KEY (`id_gejala`) REFERENCES `Gejala` (`id_gejala`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evidence_reconciliations`
--

LOCK TABLES `evidence_reconciliations` WRITE;
/*!40000 ALTER TABLE `evidence_reconciliations` DISABLE KEYS */;
/*!40000 ALTER TABLE `evidence_reconciliations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `hasil_pakar`
--

DROP TABLE IF EXISTS `hasil_pakar`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hasil_pakar` (
  `id_hasil` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_gejala` varchar(20) NOT NULL,
  `hasil` varchar(150) NOT NULL,
  `skor` int(11) DEFAULT NULL,
  `ringkasan` text DEFAULT NULL,
  `tanggal_evaluasi` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_hasil`),
  UNIQUE KEY `id_gejala` (`id_gejala`),
  CONSTRAINT `hasil_pakar_ibfk_1` FOREIGN KEY (`id_gejala`) REFERENCES `Gejala` (`id_gejala`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hasil_pakar`
--

LOCK TABLES `hasil_pakar` WRITE;
/*!40000 ALTER TABLE `hasil_pakar` DISABLE KEYS */;
INSERT INTO `hasil_pakar` VALUES (1,'G0000000000000000001','CLINICAL_MEASLES_PATTERN',3,'Demam + ruam + batuk sesuai pola klinis campak.','2026-11-01 09:45:00'),(2,'G0000000000000000002','CLINICAL_MEASLES_PATTERN',3,'Demam + ruam + konjungtivitis sesuai pola klinis campak.','2026-11-05 14:20:00'),(3,'G0000000000000000004','SAFETY_ALERT',1,'Terdapat tanda bahaya (kesulitan bernapas).','2026-11-10 20:00:00');
/*!40000 ALTER TABLE `hasil_pakar` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jawaban_gejala`
--

DROP TABLE IF EXISTS `jawaban_gejala`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jawaban_gejala` (
  `id_jawaban` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_gejala` varchar(20) NOT NULL,
  `kode_gejala` varchar(30) NOT NULL,
  `nilai` int(11) NOT NULL,
  `tanggal_input` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_jawaban`),
  UNIQUE KEY `uq_jawaban_pemeriksaan_gejala` (`id_gejala`,`kode_gejala`),
  KEY `kode_gejala` (`kode_gejala`),
  CONSTRAINT `jawaban_gejala_ibfk_1` FOREIGN KEY (`id_gejala`) REFERENCES `Gejala` (`id_gejala`),
  CONSTRAINT `jawaban_gejala_ibfk_2` FOREIGN KEY (`kode_gejala`) REFERENCES `master_gejala` (`kode_gejala`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jawaban_gejala`
--

LOCK TABLES `jawaban_gejala` WRITE;
/*!40000 ALTER TABLE `jawaban_gejala` DISABLE KEYS */;
INSERT INTO `jawaban_gejala` VALUES (1,'G0000000000000000001','DEMAM',1,'2026-11-20 09:43:02'),(2,'G0000000000000000001','BATUK',1,'2026-11-20 09:43:02'),(3,'G0000000000000000001','RUAM',1,'2026-11-20 09:43:02'),(4,'G0000000000000000002','DEMAM',1,'2026-11-20 09:43:02'),(5,'G0000000000000000002','MATA_MERAH',1,'2026-11-20 09:43:02'),(6,'G0000000000000000003','DEMAM',0,'2026-11-20 09:43:02'),(7,'G0000000000000000004','SESAK',1,'2026-11-20 09:43:02');
/*!40000 ALTER TABLE `jawaban_gejala` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `kioskdevices`
--

DROP TABLE IF EXISTS `kioskdevices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `kioskdevices` (
  `id_device` varchar(36) NOT NULL,
  `nama_device` varchar(100) NOT NULL,
  `secret_hash` varchar(255) NOT NULL,
  `aktif` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_device`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `kioskdevices`
--

LOCK TABLES `kioskdevices` WRITE;
/*!40000 ALTER TABLE `kioskdevices` DISABLE KEYS */;
INSERT INTO `kioskdevices` VALUES ('c0ffee00-0000-4000-8000-000000000001','MeaslesCare Kiosk Demo 01','$2b$12$IvBlK35Qc1.pL/ejnEvGc.uNnArrmsDYKSFS29wVOHWctS33iblem',1,'2026-11-20 09:43:02');
/*!40000 ALTER TABLE `kioskdevices` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `kiosksessions`
--

DROP TABLE IF EXISTS `kiosksessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `kiosksessions` (
  `id_session` varchar(36) NOT NULL,
  `id_device` varchar(36) NOT NULL,
  `token_hash` varchar(64) NOT NULL,
  `expires_at` datetime NOT NULL,
  `revoked` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_session`),
  UNIQUE KEY `token_hash` (`token_hash`),
  KEY `ix_kiosksessions_id_device` (`id_device`),
  CONSTRAINT `kiosksessions_ibfk_1` FOREIGN KEY (`id_device`) REFERENCES `kioskdevices` (`id_device`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `kiosksessions`
--

LOCK TABLES `kiosksessions` WRITE;
/*!40000 ALTER TABLE `kiosksessions` DISABLE KEYS */;
/*!40000 ALTER TABLE `kiosksessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `master_gejala`
--

DROP TABLE IF EXISTS `master_gejala`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `master_gejala` (
  `kode_gejala` varchar(30) NOT NULL,
  `nama_gejala` varchar(100) NOT NULL,
  `deskripsi` text DEFAULT NULL,
  `jenis` enum('GEJALA','TANDA_BAHAYA','PARAMETER') NOT NULL,
  `aktif` tinyint(1) NOT NULL,
  PRIMARY KEY (`kode_gejala`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `master_gejala`
--

LOCK TABLES `master_gejala` WRITE;
/*!40000 ALTER TABLE `master_gejala` DISABLE KEYS */;
INSERT INTO `master_gejala` VALUES ('BATUK','Batuk','Pasien mengalami batuk.','GEJALA',1),('DEMAM','Demam','Pasien mengalami demam.','GEJALA',1),('DIARE','Diare','Pasien mengalami diare.','GEJALA',1),('KEJANG','Kejang','Pasien mengalami kejang.','TANDA_BAHAYA',1),('KOPLIK','Bercak Koplik','Terdapat bercak Koplik.','GEJALA',1),('MATA_MERAH','Mata Merah','Gejala konjungtivitis.','GEJALA',1),('PENURUNAN_KESADARAN','Penurunan Kesadaran','Terdapat perubahan tingkat kesadaran.','TANDA_BAHAYA',1),('PILEK','Pilek','Pasien mengalami pilek atau coryza.','GEJALA',1),('RUAM','Ruam Makulopapular','Terdapat ruam makulopapular pada kulit.','GEJALA',1),('RUAM_MENYELURUH','Ruam Menyeluruh','Ruam tersebar secara menyeluruh pada tubuh.','GEJALA',1),('SESAK','Sesak Napas','Pasien mengalami kesulitan bernapas.','TANDA_BAHAYA',1),('SUHU','Suhu Tubuh','Nilai suhu diambil dari kolom Gejala.Suhu.','PARAMETER',1);
/*!40000 ALTER TABLE `master_gejala` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `patient_cards`
--

DROP TABLE IF EXISTS `patient_cards`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `patient_cards` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `rfid_uid` varchar(64) NOT NULL,
  `NIK` varchar(16) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_patient_cards_rfid_uid` (`rfid_uid`),
  KEY `NIK` (`NIK`),
  CONSTRAINT `patient_cards_ibfk_1` FOREIGN KEY (`NIK`) REFERENCES `Users` (`NIK`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `patient_cards`
--

LOCK TABLES `patient_cards` WRITE;
/*!40000 ALTER TABLE `patient_cards` DISABLE KEYS */;
INSERT INTO `patient_cards` VALUES (1,'E0040100ABCDEF0001','3201234567890002','2026-11-20 09:43:02'),(2,'E0040100ABCDEF0002','3201234567890003','2026-11-20 09:43:02'),(3,'E0040100ABCDEF0003','3201234567890004','2026-11-20 09:43:02');
/*!40000 ALTER TABLE `patient_cards` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'db_huawei'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-20 10:27:07
