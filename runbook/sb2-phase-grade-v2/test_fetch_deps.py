# SPDX-License-Identifier: Apache-2.0
"""Tests for fetch_deps 0.2.0 (MV2, Munim, Inc.; made with AI agents). The VOTABLE below mirrors the
layout the AIP Gaia TAP mirror returned on 27 Nov 2026 (namespace v1.3, TABLEDATA, empty TD = null)."""
import unittest

import fetch_deps as D

VOT = """<?xml version="1.0"?>
<VOTABLE version="1.3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
 <RESOURCE type="results">
  <INFO name="QUERY_STATUS" value="OK"/>
  <TABLE name="result">
   <FIELD name="source_id" datatype="long"/>
   <FIELD name="period" datatype="double"/>
   <FIELD name="period_error" datatype="float"/>
   <FIELD name="eccentricity" datatype="double"/>
   <FIELD name="eccentricity_error" datatype="float"/>
   <FIELD name="arg_periastron" datatype="double"/>
   <FIELD name="arg_periastron_error" datatype="float"/>
   <FIELD name="t_periastron" datatype="double"/>
   <FIELD name="t_periastron_error" datatype="float"/>
   <FIELD name="nss_solution_type" datatype="char" arraysize="*"/>
   <DATA><TABLEDATA>
    <TR><TD>2825104215999846144</TD><TD>2.4459244940177975</TD><TD>2.3348732e-05</TD><TD>0.06799525074794158</TD><TD>0.006550011</TD><TD>240.43638271739127</TD><TD>5.832804</TD><TD>-0.6081781478955065</TD><TD>0.039145075</TD><TD>SB2</TD></TR>
    <TR><TD>2186746353538849408</TD><TD>5.223366008623945</TD><TD>0.00012772053</TD><TD></TD><TD></TD><TD></TD><TD></TD><TD>-2.2187927920734767</TD><TD>0.00858001</TD><TD>SB2C</TD></TR>
   </TABLEDATA></DATA>
  </TABLE>
 </RESOURCE>
</VOTABLE>
"""

VOT_ERR = """<?xml version="1.0"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
 <RESOURCE type="results"><INFO name="QUERY_STATUS" value="ERROR">column foo not found</INFO></RESOURCE>
</VOTABLE>
"""

CSV = ("source_id,period,period_error,eccentricity,eccentricity_error,arg_periastron,arg_periastron_error,"
       "t_periastron,t_periastron_error,nss_solution_type\n"
       "2825104215999846144,2.4459244940177975,2.3348732e-05,0.06799525074794158,0.006550011,"
       "240.43638271739127,5.832804,-0.6081781478955065,0.039145075,SB2\n")


class TestParse(unittest.TestCase):
    def test_votable(self):
        rows = D.parse_tap(VOT)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_id"], "2825104215999846144")
        self.assertEqual(rows[0]["period"], "2.4459244940177975")
        self.assertEqual(rows[0]["nss_solution_type"], "SB2")
        self.assertEqual(rows[1]["eccentricity"], "")
        self.assertEqual(rows[1]["nss_solution_type"], "SB2C")
        self.assertEqual(sorted(rows[1].keys()), sorted(D.COLS))

    def test_csv(self):
        rows = D.parse_tap(CSV)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["t_periastron"], "-0.6081781478955065")

    def test_error_raises(self):
        with self.assertRaises(RuntimeError):
            D.parse_tap(VOT_ERR)

    def test_url_is_get(self):
        u = D.orbit_query_url(["1", "2"])
        self.assertTrue(u.startswith(D.AIP + "?"))
        self.assertIn("IN+%281%2C2%29", u)


if __name__ == "__main__":
    unittest.main()
